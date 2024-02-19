import shutil
import uuid
from pathlib import Path

import applescript
import click
import humanize
from keynote_parser.file_utils import process
from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

from minimize_ninja.common import configure_logger, get_logger, read_config
from minimize_ninja.keynote import KeynoteFile, TiffyYaml


@click.group(help=f"MinimizeNinja version 0.0.2")
@click.option("-v", "--verbose", "verbosity", help="Increase verbosity", count=True)
@click.option("--log-file", "log_file", help="Log file to sent all output to")
# @click.version_option(__version__)
def cli(verbosity, log_file):
    configure_logger(verbosity, log_file)
    pass


@click.command(help="Get a Keynote file into shape by losing " "unnecessary weight")
@click.option(
    "-q",
    "--quality",
    "quality",
    default=0,
    type=int,
    show_default=True,
    help="Control the quality of the resulting Keynote file. The "
    "level [0–3] controls quality vs. size with 0 resulting "
    "in the highest quality/largest size and 3 in lowest "
    "quality/smallest size. Zero is the default and best "
    "setting to retain a reasonable quality to store "
    "your Keynote files. Levels 1–3 are targeted for creating "
    "reasonably-sized PDF exports. DO NOT USE LEVELS 1–3 TO "
    "OPTIMIZE YOUR KEYNOTE FILE PERMANENTLY AS IMAGES WILL BE "
    "DEGRADED IN QUALITY!",
)
@click.option(
    "-p",
    "--export-pdf",
    "export_pdf",
    help="Export Keynote presentation to PDF after optimizing",
    is_flag=True,
)
@click.option(
    "--keep-unpacked",
    "keep_unpacked",
    help="Do not delete unpacked Keynote data",
    is_flag=True,
)
@click.option(
    "--resize-factor",
    "resize_factor",
    default=2.0,
    show_default=True,
    help="Resizing factor to keep acceptable resolution for images",
)
@click.option(
    "--jpeg-compression",
    "jpeg_compression",
    default=85,
    show_default=True,
    help="JPEG quality setting for compression (0–100, default: 85)",
)
@click.option(
    "--png-convert",
    "png_convert",
    is_flag=True,
    help="Try to convert PNG files to JPEG to save additional space",
)
@click.argument("keynote_file", type=click.Path(exists=True))
def slim(
    quality,
    keynote_file,
    export_pdf,
    keep_unpacked,
    resize_factor,
    jpeg_compression,
    png_convert,
):
    resources = read_config()
    logger = get_logger()
    console = resources["console"]
    path_packed = Path(keynote_file)
    # path_unpacked = Path.cwd()
    # filename_repacked = str(path_packed.stem) + '_tiffy.key'
    # path_repacked = Path.cwd() / filename_repacked

    kf = KeynoteFile(resources, path_keynote=path_packed)

    match quality:
        case 0:
            # Nothing to do, use standard settings defined above.
            pass
        case 1:
            resize_factor = 2.0
            jpeg_compression = 80
            png_convert = True
            export_pdf = True
        case 2:
            resize_factor = 1.5
            jpeg_compression = 75
            png_convert = True
            export_pdf = True
        case 3:
            resize_factor = 1.0
            jpeg_compression = 70
            png_convert = True
            export_pdf = True

    # while path_unpacked.exists():
    #     path_unpacked = Path.cwd() / str(uuid.uuid4())[0:8]

    if resize_factor < 2.0:
        console.print()
        logger.warning(
            "You selected a resizing factor of below 2.0! This "
            "can lead to lost image information and blurry pictures"
            ", especially on Retina screens. Use this setting for "
            "exporting to PDF only and keep your original Keynote "
            "file with the best resolution images!"
        )
        console.print()

    if jpeg_compression < 80:
        console.print()
        logger.warning(
            "You selected a JPEG quality setting below 80! This "
            "can lead to lost image information and ugly pictures"
            "with artifacts. Use this setting for "
            "exporting to PDF only and keep your original Keynote "
            "file with the best resolution images!"
        )
        console.print()

    # logger.info(f'Unpacking Keynote file {str(path_packed)}…')
    # console.print()
    # process(str(path_packed), str(path_unpacked), replacements=[])
    kf.unpack()
    console.print()

    metadata = kf.metadata

    # path_index = path_unpacked / 'Index'
    # path_metadata = path_index / 'Metadata.iwa.yaml'
    # path_data = path_unpacked / 'Data'

    # metadata = TiffyYaml(path_metadata)

    # images_dict = {}
    logger.debug(f"Searching images in Metadata.iwa.yaml…")
    images_dict = kf.images_dict
    # for chunk in metadata.yaml['chunks']:
    #     for archive in chunk['archives']:
    #         for object in archive['objects']:
    #             for data in object.get('datas', []):
    #                 if data['fileName'] != '':
    #                     image = ImageFile(data, path_data, resources)
    #                     # images.append(image)
    #                     images_dict[image.identifier] = image
    logger.debug(f"…done! Found {len(images_dict.keys())} image files.")

    tiffies = [
        image for id, image in images_dict.items() if "tif" in image.filename.suffix
    ]
    pngs = [
        image for id, image in images_dict.items() if "png" in image.filename.suffix
    ]

    if tiffies:
        logger.info(
            f"Found {len(tiffies)} TIFF files 🙄. Did someone have"
            f" too many midnight snacks? Time to lose some weight! 💪"
        )
        tiff_file_names = [tiff.filename.name for tiff in tiffies]
        logger.debug(f'List of TIFF files: {", ".join(tiff_file_names)}')

        logger.info(f"Building personal training plans to get images into " f"shape…")
        for tiff in tqdm(tiffies):
            tiff.convert()

        sizes_original = sum([tiff.size_original for tiff in tiffies])
        sizes_converted = sum([tiff.size_converted for tiff in tiffies])
        sizes_original_humanized = humanize.naturalsize(sizes_original)
        sizes_converted_humanized = humanize.naturalsize(sizes_converted)
        reduction = (1.0 - (sizes_converted / sizes_original)) * 100.0

        logger.info(
            f"…done! Reducing TIFFs with a size of "
            f"{sizes_original_humanized} to "
            f"{sizes_converted_humanized} ({reduction:.1f} %"
            f" reduction). 🚀"
        )
        metadata.save()
    else:
        logger.info(f"No TIFF files in {str(path_packed)}.")
        pass

    if pngs and png_convert:
        console.print()
        logger.info(
            f"Found {len(pngs)} PNG files 🙄. Let us check for "
            f"weight-loss potential…"
        )
        png_file_names = [png.filename.name for png in pngs]
        logger.debug(f'List of PNG files: {", ".join(png_file_names)}')

        logger.info(f"Building personal training plans to get images into " f"shape…")
        for png in tqdm(pngs):
            png.convert(jpeg_compression=jpeg_compression)

        sizes_original = sum([png.size_original for png in pngs])
        sizes_converted = sum([png.size_converted for png in pngs])
        sizes_original_humanized = humanize.naturalsize(sizes_original)
        sizes_converted_humanized = humanize.naturalsize(sizes_converted)
        reduction = (1.0 - (sizes_converted / sizes_original)) * 100.0

        logger.info(
            f"…done! Reducing PNGs with a size of "
            f"{sizes_original_humanized} to "
            f"{sizes_converted_humanized} ({reduction:.1f} %"
            f" reduction). 🚀"
        )
        metadata.save()

    console.print()
    logger.info(
        f"Found {len(images_dict.keys())} tasty images. 🧁 Let's see "
        f"how we can cut some calories by optimizing your diet plan "
        f"(i.e. resize images to an optimal resolution)…"
    )
    all_yaml = [TiffyYaml(file) for file in kf.path_index.iterdir()]
    logger.debug(
        f"Searching {len(all_yaml)} metadata YAML files for "
        f"references to the {len(images_dict.keys())} image files…"
    )
    for yaml_file in all_yaml:
        for chunk in yaml_file.yaml["chunks"]:
            for archive in chunk["archives"]:
                for object in archive["objects"]:
                    if object["_pbtype"] == "TSD.ImageArchive":
                        identifier = object.get("data", {}).get("identifier", 0)
                        if identifier in images_dict:
                            images_dict[identifier].add_slide_reference(
                                yaml_file, object
                            )
                    if object["_pbtype"] == "KN.SlideStyleArchive":
                        if "image" in object.get("slideProperties", {}).get("fill", {}):
                            identifier = (
                                object.get("slideProperties", {})
                                .get("fill", {})
                                .get("image", {})
                                .get("imagedata", {})
                                .get("identifier", 0)
                            )
                            if identifier in images_dict:
                                images_dict[identifier].add_slide_style_reference(
                                    yaml_file, object
                                )

    for id, image in tqdm(images_dict.items()):
        image.resize(max_ratio_factor=resize_factor)

    sizes_converted = sum([image.size_converted for id, image in images_dict.items()])
    sizes_resized = sum([image.size_resized for id, image in images_dict.items()])
    sizes_converted_humanized = humanize.naturalsize(sizes_converted)
    sizes_resized_humanized = humanize.naturalsize(sizes_resized)
    reduction = (1.0 - (sizes_resized / sizes_converted)) * 100.0
    logger.info(
        f"…done! Reducing images with a total size of "
        f"{sizes_converted_humanized} to "
        f"{sizes_resized_humanized} ({reduction:.1f} %"
        f" reduction) by resizing optimally. 🚀"
    )

    console.print()
    logger.info(
        f"Analyze nutrients in {len(images_dict.keys())} images. "
        f"🧁->🥬 Optimizing food healthiness (i.e. optimize image "
        f"compression)…"
    )

    # sw = Stopwatch()
    for id, image in tqdm(images_dict.items()):
        image.optimize(jpeg_compression=jpeg_compression)
    # sw.lap()

    sizes_resized = sum([image.size_resized for id, image in images_dict.items()])
    sizes_optimized = sum([image.size_optimized for id, image in images_dict.items()])
    sizes_resized_humanized = humanize.naturalsize(sizes_resized)
    sizes_optimized_humanized = humanize.naturalsize(sizes_optimized)
    reduction = (1.0 - (sizes_optimized / sizes_resized)) * 100.0
    logger.info(
        f"…done! Reducing images with a total size of "
        f"{sizes_resized_humanized} to "
        f"{sizes_optimized_humanized} ({reduction:.1f} %"
        f" reduction) by running compression optimizations. 🚀"
    )

    console.print()
    # logger.info(f'Re-packing Keynote file {path_repacked.name}…')
    # console.print()
    # process(str(path_unpacked), str(path_repacked), replacements=[])
    kf.repack()
    console.print()

    size_original = kf.path_keynote.stat().st_size
    size_optimized = kf.path_repacked.stat().st_size
    size_original_humanized = humanize.naturalsize(size_original)
    size_optimized_humanized = humanize.naturalsize(size_optimized)
    reduction = (1.0 - (size_optimized / size_original)) * 100.0
    logger.info(
        f"MinimizeNinja is finished! 💪 Reducing Keynote file from "
        f"{size_original_humanized} to "
        f"{size_optimized_humanized} ({reduction:.1f} %"
        f" reduction). 🚀"
    )

    if not keep_unpacked:
        logger.debug(f"Removing temporary files in {str(kf.path_unpacked)}…")
        shutil.rmtree(kf.path_unpacked)

    if export_pdf:
        filename_pdf = str(kf.path_keynote.stem) + ".pdf"
        path_pdf = Path.cwd() / filename_pdf
        logger.info(
            f"Calling AppleScript to export optimized Keynote file to "
            f"{filename_pdf}…"
        )
        logger.info(
            f"Keynote will open soon and should close after exporting. In case"
            f" anything goes wrong you may need to quit Keynote before Miss "
            f"Tiffy can continue."
        )
        script = f"""
            tell application "Keynote"
              set keynote_file to open ("{kf.path_repacked}" as POSIX file)
              export keynote_file to ("{path_pdf}" as POSIX file) as PDF with properties {{ PDF image quality: Better, skipped slides: false, all stages: true }}
              close keynote_file saving no
            end tell
            """
        r = applescript.run(script)
        if r.code == 0:
            logger.debug(f"Removing optimized Keynote file…")
            kf.path_repacked.unlink()


cli.add_command(slim)


def main():
    try:
        cli()
    except SystemExit:
        pass
    except:
        crash_message = f"""
MinimizeNinja just crashed, too bad. Don't panic!

Here is what you can do:

1. Make sure MinimizeNinja is up to date.

2. If this did not help to solve the issue, create a bug report under
   [b]https://github.com/point8/minimize-ninja/issues[/b]. Please provide the
   [b]full(!)[/b] output of MinimizeNinja via copy-paste or as a screenshot in the
   issue (including this message and the following output!).

Diagnostics:
MinimizeNinja version: 0.0.2
        """
        console = Console()
        console.print_exception(show_locals=True)
        console.print("\n\n")
        console.print(
            Panel.fit(crash_message, title=":warning-emoji: [bold red] Oops…[/]")
        )
