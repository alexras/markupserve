## About

MarkupServe is a simple web server that renders provides convenient access to a
tree of documents written in your favorite markup language. I wrote it because
I wanted an easy way to interact with a tree of Markdown files without having
to keep rendering them over and over again.

With MarkupServe, you can navigate a hierarchy of directories containing
markup-language files in the same way you would navigate through an Apache
directory tree. When the server is asked to retrieve a document written in the
markup language, it passes the document through the converter of your choice
and returns the resulting HTML.

## Installation

**NOTE:**: Markupserve has only been tested with Python 2. Pull requests that
  introduce Python 3 support are welcome, but I have no plans to introduce
  Python 3 compatibility any time soon.

Check out this repo and run

`pip install -r requirements.txt`

MarkupServe uses [bottle][bottle] for serving, [jinja2][jinja] for templates
and [whoosh][whoosh] for indexing and search.

If you're running an older version of Python, you may also need to install
`argparse`.

MarkupServe comes with a renderer (`renderer.py`) that does Markdown rendering
and syntax highlighting for [GitHub-Flavored Markdown][gfm]-style fenced code
blocks. To use the renderer, install its dependencies by running

`pip install -r requirements.renderer.txt`

The default renderer uses [misaka][misaka] for parsing Markdown,
[houdini.py][houdini] for HTML-escaping text and [Pygments][pygments] for
syntax highlighting.

## Configuration

MarkupServe reads its configuration from a config file (it looks for
`config.cfg` by default). It requires that you define the following parameters:

* `document_root`: the root directory from which to serve documents
* `port`: the port on which the server itself runs
* `converter_binary`: the converter program used to convert markup
  documents. This can be specified as a relative or absolute path, or you can
  give a binary in your `PATH`
* `markup_suffixes`: a comma-delimited list of the file suffixes that
  MarkupServe should interpret as the suffixes of files written in the target
  markup language
* `index_root`: the root directory where MarkupServe's search indices will be
  stored.

Here's an example minimal configuration file (also in `config.cfg.sample`):

    [markupserve]
    document_root = ~/Documents
    port=8080
    converter_binary = ./renderer.py
    markup_suffixes = .md, .text, .mkd, .markdown
    index_root = ~/.markupserve_index

You can hack the CSS for files and directory listings by editing
`static/file_style.css` and `static/dir_style.css`, resp.

## Views

"Views" of directories can be configured on a per-directory basis by adding a
file named `.markupserve_dir_config` to a directory. A list of supported views
and information about their settings is given below.

### Calendar View

If you have a bunch of files of the form

`<common prefix><year>-<month>-<day><common suffix>`

in a directory, you can organize them into a calendar by month and year. To do
this, create a `.markupserve_dir_config` file with the following contents:

```
[style]
name: calendar
file_prefix: <your common prefix here>
file_suffix: <your common suffix here>
```

For example, I've got a bunch of research logs in a folder called "Research
Logs". The logs are consistently named as "Research Log YYYY-MM-DD.md". In my
case, `file_prefix` is "Research Log " and `file_suffix` is ".md".

## Acknowledgments

The icons used for file navigation are from
[The Crystal Project][crystal-project]. The default CSS used to render files is
[iAWriterCSS][moritzz-iAWriterCSS], which is a condensed versions of the styles
used in [iA Writer][ia-writer].

[mmd]: http://fletcherpenney.net/multimarkdown/
[bottle]: http://bottlepy.org/docs/dev/
[jinja]: http://jinja.pocoo.org/
[crystal-project]: http://www.everaldo.com/crystal/
[moritzz-iAWriterCSS]: https://github.com/moritzz/iAWriterCSS
[ia-writer]: http://www.iawriter.com/
[whoosh]: https://bitbucket.org/mchaput/whoosh/wiki/Home
[misaka]: http://misaka.61924.nl/
[houdini]: http://python-houdini.61924.nl/
[pygments]: http://pygments.org/
