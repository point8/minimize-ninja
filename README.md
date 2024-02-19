# MinimizeNinja

MinimizeNinja. Compress Apple Keynote presentations files like a 🥷

[**Try out!**](https://minimize.ninja/)

## Abstract

We developed MinimizeNinja out of necessity, because Keynote does not allow creating proper-looking yet reasonably sized PDF files. For certain Keynote files, the resulting PDFs are either too large or they look shitty. You can even get the worst of both and end up with shitty-looking _and_ large files. 🎉

MinimizeNinja is a Python-based command line tool that unpacks Keynote files, analyzes graphic files used inside the presentation and utilizes several optimizations to achieve a smaller Keynote file. Exporting PDFs from these reduced files results in smaller PDFs that still look good. 

## Details

MinimizeNinja can be used to optimize Keynote files. Either to reduce the file size of the Keynote file itself (in order to keep this reduced yet still high quality Keynote file) or – more aggressively – to create an even smaller Keynote file with reasonable quality impact to export this to a small PDF file that can be send to other people via mail. In the latter case, keeping this reduced Keynote file is _not_ advisable as the graphics quality will be impacted.

These optimizations are performed:

1. All TIFF files within the Keynote file are converted to JPEG and PNG, replacing the TIFF by the smaller of the latter. As TIFF files inside Keynote presentations are rarely compressed, this usually saves a lot of space.
2. Optional, applicable for PDF export: All PNG files are test-converted to JPEG. In case the JPEG variant is smaller than the PNG, the JPEG is being kept. As PNG is a lossless file and JPEG uses lossy (and thus quality-degrading) compression, this will introduce some mild quality loss.
3. All graphics are checked for the resolution they are used with inside the presentation. In case the image resolution is much larger than the used resolution within the presentation, the files are resized so that they still stay crisp on 4K/Retina displays, but do not waste space unnecessarily. E.g. if you add a 15 megapixel photo as a small stamp graphic inside a Keynote slide of 300 x 400 pixels, MinimizeNinja will resize the file to 600 x 800 pixels (reducing 15 MP -> 0.5 MP).
4. Image optmization packages like MozJPEG and Oxipng are run on all images. These tools try to compress the files even more, get rid of unnecessary metadata etc. In many cases, these tools can reduce files by additional 5–40% without losing quality.

## Requirements

### MozJPEG

You need to install MozJPEG:

```
brew install mozjpeg
```

Afterwards, there will be a message telling you that mozjpeg is keg-only, which
means it was not symlinked into /opt/homebrew. Therefore you need to execute the
printed line below to add the mozjpeg binaries to your $PATH.

## Caveats

- Depends on [`keynote_parser`](https://pypi.org/project/keynote-parser/) which in its most current version is not able to
  unpack certain Keynote files in case these contain tables or charts.

## Troubleshooting

### Q: I get the message "Unrecognized input file format --- perhaps you need -targa"

Sometimes it happens that you get messages like 

```
ERROR    cjpeg was unable to run on ImageFile(…):
ERROR    Unrecognized input file format --- perhaps you need -targa 
```

This is an error message in case MozJPEG is not able to parse a certain JPEG
file for size optimization. Actually, the `-targa` hint is misleading in my
experience. These files are _not_ TARGA files and it is unclear to me why
MozJPEG is not able to parse these files. In every case I checked, these files
seemed perfectly fine and I could open them with every other tool I tried. You
can safely ignore these errors.
