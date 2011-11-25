## About

MarkupServe is a simple web server that renders provides convenient access to a tree of documents written in your favorite markup language. I wrote it because I wanted an easy way to interact with a tree of Markdown files without having to keep rendering them over and over again.

With MarkupServe, you can navigate a hierarchy of directories containing markup-language files in the same way you would navigate through an Apache directory tree. When the server is asked to retrieve a document written in the markup language, it passes the document through the converter of your choice (I use [multimarkdown][mmd] personally) and returns the resulting HTML.

## Dependencies

I've tested MarkupServe with Python 2.7.1 on Mac OS X 10.7. I'm pretty sure it will work under both OS X and Linux and on Python versions in the 2.6+ range. YMMV.

MarkupServe requires the following Python libraries (all readily available through PyPi):

* [bottle][bottle]
* [jinja2][jinja]

It also makes use of Python's `argparse` library; you may need to download a backport if you're running an older version of Python.

## Configuration

MarkupServe reads its configuration from a config file (it looks for `config.cfg` by default). It requires that you define four parameters:

* `document_root`: the root directory from which to serve documents
* `port`: the port on which the server itself runs
* `converter_binary`: the converter program used to convert markup documents (can be specified as a relative or absolute path, or you can give a binary in your `PATH`)
* `markup_suffixes`: a comma-delimited list of the file suffixes that MarkupServe should interpret as the suffixes of files written in the target markup language

Here's an example minimal configuration file:

    [markupserve]
    document_root = ~/Documents/Notes
    port=8080
    converter_binary = multimarkdown
    markup_suffixes = .md, .text, .mkd, .markdown

You can hack the CSS for directory listings and converted files by editing `static/dir_style.css` and `static/file_style.css`, resp.

## Acknowledgments

The icons used for file navigation are from [The Crystal Project][crystal-project]. The default CSS used to render files is [iAWriterCSS][moritzz-iAWriterCSS], which is a condensed versions of the styles used in [iA Writer][ia-writer].

[mmd]: http://fletcherpenney.net/multimarkdown/
[bottle]: http://bottlepy.org/docs/dev/
[jinja]: http://jinja.pocoo.org/
[crystal-project]: http://www.everaldo.com/crystal/
[moritzz-iAWriterCSS]: https://github.com/moritzz/iAWriterCSS
[ia-writer]: http://www.iawriter.com/