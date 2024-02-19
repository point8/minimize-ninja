import yaml
from pathlib import Path
from wand.image import Image
from keynote_parser.file_utils import process
import humanize
import oxipng
import subprocess
import uuid


class KeynoteFile(object):
    def __init__(self, resources, path_keynote=None, path_unpacked=None):
        self._resources = resources
        self._logger = resources['logger']
        if path_keynote is not None:
            self._path_keynote = path_keynote
            self._path_unpacked = Path.cwd()
            self._is_unpacked = False
            while self._path_unpacked.exists():
                self._path_unpacked = Path.cwd() / str(uuid.uuid4())[0:8]
            filename_repacked = str(self._path_keynote.stem) + '_tiffy.key'
        elif path_unpacked is not None:
            self._path_keynote = None
            self._path_unpacked = path_unpacked
            self._is_unpacked = True
            filename_repacked = str(self._path_unpacked.stem) + '_tiffy.key'
        self._path_repacked = Path.cwd() / filename_repacked
        self._images_dict = None
        self._slides = None
        self._metadata = None

    def __repr__(self):
        if self.path_keynote is not None:
            return f'KeynoteFile({self.path_keynote})'
        else:
            return f'KeynoteFile({self.path_unpacked})'

    def unpack(self):
        if not self.is_unpacked:
            self._logger.info(f'Unpacking Keynote file {str(self.path_keynote)}…')
            print()
            process(str(self.path_keynote), str(self.path_unpacked), replacements=[])
            self._is_unpacked = True
        else:
            self._logger.error(f'{self} already unpacked! Will not unpack again.')

    def repack(self):
        if self.is_unpacked:
            self._logger.info(f'Re-packing Keynote file {self.path_repacked.name}…')
            print()
            process(str(self.path_unpacked), str(self.path_repacked), replacements=[])
        else:
            self._logger.error(f'{self} not yet unpacked! Cannot repack before unpacking.')

    def _load_metadata(self):
        if not self.is_unpacked:
            self._logger.error(f'{self} cannot load metadata as Keynote file is not unpacked yet!')
            return
        path_metadata = self.path_unpacked / 'Index' / 'Metadata.iwa.yaml'
        self._metadata = TiffyYaml(path_metadata)

    def _load_image_metadata(self):
        if not self.is_unpacked:
            self._logger.error(f'{self} cannot load image metadata as Keynote file is not unpacked yet!')
            return
        # path_metadata = self.path_unpacked / 'Index' / 'Metadata.iwa.yaml'
        # self._metadata = TiffyYaml(path_metadata)
        self._images_dict = {}
        self._logger.debug(f'Searching images in Metadata.iwa.yaml…')
        for chunk in self.metadata.yaml['chunks']:
            for archive in chunk['archives']:
                for obj in archive['objects']:
                    for data in obj.get('datas', []):
                        if data['fileName'] != '':
                            image = ImageFile(data, self.path_data,
                                              self._resources)
                            # images.append(image)
                            self._images_dict[image.identifier] = image

    def _load_slides(self):
        if not self.is_unpacked:
            self._logger.error(f'{self} cannot load image metadata as Keynote file is not unpacked yet!')
            return
        path_document = self.path_unpacked / 'Index'  / 'Document.iwa.yaml'
        self._document = TiffyYaml(path_document)
        self._slides = []
        for chunk in self._document.yaml['chunks']:
            for archive in chunk['archives']:
                for obj in archive['objects']:
                    if obj['_pbtype'] == 'KN.SlideNodeArchive':
                        slide = KeynoteSlide(obj, path_unpacked)
                        self._slides.append(slide)
                        slide.build_file_references(self.images_dict)
        slides_numbered = [
            slide for slide in self._slides
            if not slide.is_skipped
        ]
        for number, slide in enumerate(slides_numbered):
            slide.slide_number = number + 1

    @property
    def is_unpacked(self):
        return self._is_unpacked

    @property
    def path_keynote(self):
        return self._path_keynote

    @property
    def path_unpacked(self):
        return self._path_unpacked

    @property
    def path_unpacked(self):
        return self._path_unpacked

    @property
    def path_repacked(self):
        return self._path_repacked

    @property
    def path_data(self):
        if not self.is_unpacked:
            return None
        else:
            return self.path_unpacked / 'Data'

    @property
    def path_index(self):
        if not self.is_unpacked:
            return None
        else:
            return self.path_unpacked / 'Index'

    @property
    def images_dict(self):
        if self._images_dict is None:
            self._load_image_metadata()
        return self._images_dict

    @property
    def metadata(self):
        if self._metadata is None:
            self._load_metadata()
        return self._metadata

    @property
    def slides(self):
        if self._slides is None:
            self._load_slides()
        return self._slides


class TiffyYaml(object):
    def __init__(self, path):
        self._path = path
        with open(self._path, "r") as stream:
            try:
                self._yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def __repr__(self):
        return f'TiffyYaml({self._path})'

    @property
    def yaml(self):
        return self._yaml

    def save(self):
        with open(self._path, 'w') as file:
            yaml.dump(self._yaml, file)


class ImageFile(object):
    def __init__(self, metadata, path_data, resources):
        self._resources = resources
        self._logger = resources['logger']
        self._metadata = metadata
        self._filename = Path(self._metadata['preferredFileName'])
        self._filename_package = self._metadata['fileName']
        self._path = path_data / self._filename_package
        self._size_original = self._path.stat().st_size
        self._size_converted = self._path.stat().st_size
        self._size_resized = self._path.stat().st_size
        self._size_optimized = self._path.stat().st_size
        self._identifier = self._metadata['identifier']
        self._slide_references = []
        self._slide_style_references = []

    def __repr__(self):
        natural_size = humanize.naturalsize(self._path.stat().st_size)
        return f'ImageFile({self._filename}, {natural_size})'

    def add_slide_reference(self, yaml_file, data):
        self._slide_references.append((yaml_file, data))

    def add_slide_style_reference(self, yaml_file, data):
        self._slide_style_references.append((yaml_file, data))

    @property
    def filename(self):
        return self._filename

    @property
    def identifier(self):
        return self._identifier

    @property
    def size_current(self):
        return self._path.stat().st_size

    @property
    def size_original(self):
        return self._size_original

    @property
    def size_converted(self):
        return self._size_converted

    @property
    def size_resized(self):
        return self._size_resized

    @property
    def size_optimized(self):
        return self._size_optimized

    @property
    def lost_weight_converted(self):
        return 1.0 - float(self.size_converted) / float(self.size_original)

    @property
    def lost_weight_resized(self):
        return 1.0 - float(self.size_resized) / float(self.size_converted)

    @property
    def lost_weight_optimized(self):
        return 1.0 - float(self.size_optimized) / float(self.size_resized)

    @property
    def slide_references(self):
        return self._slide_references

    @property
    def slide_style_references(self):
        return self._slide_style_references

    @property
    def has_slide_references(self):
        return (self._slide_references or self._slide_style_references)

    def convert(self, formats=['png', 'jpg'], jpeg_compression=85):
        natural_size = humanize.naturalsize(self.size_original)
        self._logger.debug(f'Working on {self.filename.name} with '
                           f'{natural_size}…')
        path_original = self._path
        with Image(filename=self._path) as image:
            format_blobs = []
            has_alpha = image.alpha_channel
            for format in formats:
                if format in ['jpg'] and has_alpha:
                    continue
                self._logger.debug(f'  Trying {format}…')
                image.format = format
                if format == 'jpg':
                    image.compression_quality = jpeg_compression
                blob = image.make_blob()
                format_blobs.append((format, len(blob), blob))
                natural_size = humanize.naturalsize(len(blob))
                self._logger.debug(f'  achieving {natural_size}.')

            format_blobs.sort(key=lambda x: x[1])
            # image.format = format
            # image.save(filename=self._path.with_suffix(f'.{format}'))
            format = format_blobs[0][0]
            if format_blobs[0][1] >= self._size_original:
                self._logger.debug(
                    f'Conversion to best format ({format}) results in even '
                    f'larger file than before. Will not convert.')
                return

            self._size_converted = format_blobs[0][1]
            self._size_resized = self._size_converted
            self._size_optimized = self._size_converted
            self._logger.debug(f'  Picking {format} and losing '
                               f'{(self.lost_weight_converted * 100.0):.1f}%!')
            with open(self._path.with_suffix(f'.{format}'), 'wb') as file:
                file.write(format_blobs[0][2])
        self._filename = self._filename.with_suffix(f'.{format}')
        self._path = self._path.with_suffix(f'.{format}')
        self._metadata['preferredFileName'] = self._filename.name
        self._metadata['fileName'] = self._path.name
        if self._path != path_original:
            path_original.unlink()

    def resize(self, max_ratio_factor=2.0):
        max_ratio = 1.0

        if (self.filename.suffix.lower() in ['.png', '.jpg', '.gif', '.jpeg']
                and self.slide_references):
            with Image(filename=self._path) as img:
                height = img.size[1]
            # TODO: original size not from YAML, but from file itself!
            ratios = [
                data['originalSize']['height'] / height
                for yaml_file, data in self.slide_references
            ]
            max_ratio = max(ratios)
            self._logger.debug(f'{self} is being used in '
                               f'{len(self.slide_references)} slide(s). '
                               f'Maximum used resolution ratio: '
                               f'{(max_ratio * 100.0):.1f}%.')
            max_ratio *= max_ratio_factor

        if (self.filename.suffix.lower() in ['.png', '.jpg', '.gif', '.jpeg']
                and self.slide_style_references):
            with Image(filename=self._path) as img:
                height = img.size[1]
            max_ratio = 1080.0 / height

            self._logger.debug(f'{self} is being used as '
                               f'master slide background. '
                               f'Maximum used resolution ratio: '
                               f'{(max_ratio * 100.0):.1f}%.')
            max_ratio *= max_ratio_factor

        if max_ratio < 1.0:
            with Image(filename=self._path) as img:
                w = int(img.size[0] * max_ratio)
                h = int(img.size[1] * max_ratio)
                self._logger.debug(
                    f'  will resize from {img.size[0]} x {img.size[1]} '
                    f'to {w} x {h}')
                img.resize(w, h)
                img.save(filename=str(self._path))
                self._size_resized = self._path.stat().st_size
                self._size_optimized = self._size_resized
                self._logger.debug(
                    f'  Reducing size from '
                    f'{humanize.naturalsize(self._size_converted)} to '
                    f'{humanize.naturalsize(self._size_resized)} ('
                    f'{(self.lost_weight_resized * 100.0):.1f}% '
                    f'reduction).')

    def optimize(self, jpeg_compression=85, oxipng_level=6):
        if (self.filename.suffix.lower() == '.png'
                and self.has_slide_references):
            self._logger.debug(
                f'{self} will be optimized via Oxipng…')
            oxipng.optimize(self._path, self._path, level=oxipng_level)
            self._size_optimized = self._path.stat().st_size
        elif ((self.filename.suffix.lower() == '.jpeg'
                or self.filename.suffix.lower() == '.jpg')
                and self.has_slide_references):
            self._logger.debug(
                f'{self} will be optimized via MozJPEG…')
            tmp_file = str(uuid.uuid4()) + '.jpg'
            path_tmp_file = self._path.parent / tmp_file
            try:
                r = subprocess.run(
                    f'cjpeg -quality {jpeg_compression} '
                    f'-outfile "{tmp_file}" '
                    f'"{self._path.name}"',
                    shell=True, capture_output=True, cwd=self._path.parent,
                    timeout=20)
            except subprocess.TimeoutExpired:
                self._logger.error(f'cjpeg aborted due to timeout on '
                                   f'{self}:')
                self._logger.error(r.stderr.decode())
            if r.returncode != 0:
                self._logger.error(f'cjpeg was unable to run on {self}:')
                self._logger.error(r.stderr.decode())
            else:
                size_tmp = path_tmp_file.stat().st_size
                if size_tmp < (self._size_resized * 0.98):
                    path_tmp_file.rename(self._path)
                    self._size_optimized = self._path.stat().st_size
            if path_tmp_file.exists():
                path_tmp_file.unlink()
        elif (self.filename.suffix.lower() == '.pdf'
                and self.has_slide_references):
            self._logger.debug(
                f'{self} will be optimized via pdfsizeopt…')
            tmp_file = str(uuid.uuid4()) + '.pdf'
            path_tmp_file = self._path.parent / tmp_file
            try:
                r = subprocess.run(
                    f'"/Users/fkruse/Documents/Point 8/fkruse/pdfsizeopt/'
                    f'pdfsizeopt" '
                    f'"{self._path.name}" '
                    f'"{tmp_file}" ',
                    shell=True, capture_output=True, cwd=self._path.parent,
                    timeout=60)
            except subprocess.TimeoutExpired:
                self._logger.error(f'pdfsizeopt aborted due to timeout on '
                                   f'{self}:')
                self._logger.error(r.stderr.decode())
            if r.returncode != 0:
                self._logger.error(f'pdfsizeopt was unable to run on {self}:')
                self._logger.error(r.stderr.decode())
            else:
                size_tmp = path_tmp_file.stat().st_size
                if size_tmp < (self._size_resized * 0.98):
                    path_tmp_file.rename(self._path)
                    self._size_optimized = self._path.stat().st_size
            if path_tmp_file.exists():
                path_tmp_file.unlink()

        if self._size_optimized != self._size_resized:
            self._logger.debug(
                f'  Reducing size from '
                f'{humanize.naturalsize(self._size_resized)} to '
                f'{humanize.naturalsize(self._size_optimized)} ('
                f'{(self.lost_weight_optimized * 100.0):.1f}% '
                f'reduction).')
