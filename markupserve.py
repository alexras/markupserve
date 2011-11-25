#!/usr/bin/env python

from bottle import run, debug, route, abort, redirect, request, static_file
import ConfigParser
import os
import argparse
import jinja2
import subprocess
import shlex
import time

config = ConfigParser.ConfigParser()

jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'),
                               trim_blocks = True)
markup_file_suffixes = set()

def find_program(program):
    for path in os.environ["PATH"].split(os.pathsep):
        executable = os.path.join(path, program)
        if os.path.exists(executable) and os.access(executable, os.X_OK):
            return os.path.abspath(executable)
    return None

def last_modified_string(file_path):
    return time.strftime("%Y/%m/%d %I:%M:%S %p", time.localtime(
            os.path.getmtime(file_path)))

def view_dir(path, parent_path, root, sorted_by, reverse):
    files = os.listdir(path)

    listable_files = []

    for filename in files:
        if filename[0] == '.' or os.path.splitext(filename)[1] == ".resources":
            continue

        file_info = {}

        file_path = os.path.join(path, filename)

        file_info["name"] = filename

        if os.path.isdir(file_path):
            file_info["icon"] = "/static/folder.png"
        else:
            file_info["icon"] = "/static/file.png"

        file_info["link"] = os.path.join(
            "/view", os.path.relpath(file_path, root))

        file_info["last_modified"] = last_modified_string(file_path)

        listable_files.append(file_info)

    if sorted_by is not None:
        listable_files.sort(key=lambda x: x[sorted_by], reverse = reverse)

    if parent_path != None:
        parent_path_info = {
            "name" : "Parent Directory",
            "link" : os.path.relpath(parent_path, root),
            "last_modified" : last_modified_string(parent_path),
            "icon" : "/static/up.png"
            }

        listable_files.insert(0, parent_path_info)

    template = jinja_env.get_template("dir.jinja")

    page_uri = os.path.join("/view", os.path.relpath(path, root))

    return template.render(files = listable_files, path = path,
                           page_uri = page_uri, sorted_by = sorted_by,
                           reverse = reverse)

def view_file(path, root):
    file_suffix = os.path.splitext(path)[1]

    if file_suffix not in markup_file_suffixes:

        return static_file(path, root="/")

    converter_bin = os.path.abspath(config.get(
            "markupserve", "converter_binary"))

    command = shlex.split('%s "%s"' % (converter_bin, path))

    render_process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)

    (output, error) = render_process.communicate()

    if render_process.returncode != 0:
        abort(500, "Conversion of '%s' failed with error %d: %s %s"
              % (path, render_process.returncode, output, error))

    template = jinja_env.get_template("file.jinja")

    filename = os.path.splitext(os.path.basename(path))[0]

    parent_path = "/view/" + os.path.relpath(
        os.path.join(path, os.pardir), root)

    # Get rid of any Unicode garbage that Jinja might choke on
    output = output.decode("utf-8")

    return template.render(filename=filename, content=output,
                           parent=parent_path)

@route("/static/:filename")
def serve_static_file(filename):
    static_root = os.path.join(os.path.dirname(__file__), "static")

    return static_file(filename, root=static_root)

@route("/search")
def search():
    search_terms = request.GET.dict["terms"][0]

    document_root = os.path.expanduser(config.get(
            "markupserve", "document_root"))

    command = shlex.split('grep -Hir "%s" %s' % (search_terms, document_root))

    grep_process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

    (output, error) = grep_process.communicate()

    if grep_process.returncode != 0:
        abort(500, "Search failed with error %d: %s %s" % (
                grep_process.returncode, output, error))

    results = {}

    for match in output.split('\n'):
        if len(match) == 0:
            continue

        (filename, delim, line_text) = match.partition(':')

        filename = os.path.relpath(filename, document_root)

        if filename not in results:
            results[filename] = []


        results[filename].append(line_text.decode("utf-8"))

    template = jinja_env.get_template("search.jinja")
    return template.render(terms = search_terms, results = results)

@route("/view/:path#.+#")
def view(path):
    """
    Handles the viewing of a file
    """

    if "sorted_by" in request.GET.dict:
        sorted_by = request.GET.dict["sorted_by"][0]
    else:
        sorted_by = None

    reverse = "reverse" in request.GET and (
        int(request.GET.dict["reverse"][0]) == 1)

    document_root = os.path.expanduser(config.get(
            "markupserve", "document_root"))

    absolute_path = os.path.abspath(document_root + "/" + path)

    if not os.path.exists(absolute_path):
        abort(404, "The path '%s' couldn't be found" % (absolute_path))

    if os.path.isdir(absolute_path):
        if path != "/":
            parent_path = os.path.abspath(absolute_path + "/" +  os.pardir)
        else:
            parent_path = None

        return view_dir(absolute_path, parent_path, document_root,
                        sorted_by, reverse)
    else:
        return view_file(absolute_path, document_root)

@route("/")
@route("/view/")
def index():
    return view("/")

parser = argparse.ArgumentParser(
    description="serves a directory hierarchy of documents written in a "
    "markup language using on-the-fly conversion")
parser.add_argument("-c", "--config", default="config.cfg",
                    help="file containing information about markupserve's "
                    "configuration")

args = parser.parse_args()

if not os.path.exists(args.config):
    exit("Can't find config file '%s'" % (args.config))

with open(args.config, 'r') as fp:
    config.readfp(fp)

if (not config.has_section("markupserve") or
    not config.has_option("markupserve", "document_root") or
    not config.has_option("markupserve", "port") or
    not config.has_option("markupserve", "converter_binary") or
    not config.has_option("markupserve", "markup_suffixes")):
    exit("MarkupServe's configuration requires a [markupserve] section "
         "with options document_root, port, converter_binary and "
         "markup_suffixes defined")

# Rewrite the location of the converter binary if its exact location isn't given
# but it's in our PATH
converter_binary = config.get("markupserve", "converter_binary")

if not os.path.exists(converter_binary):
    converter_binary = find_program(converter_binary)

    if converter_binary != None:
        config.set("markupserve", "converter_binary", converter_binary)
    else:
        exit("Can't find converter binary '%s'" % (converter_binary))

# Populate valid markup file suffixes
for suffix in config.get("markupserve", "markup_suffixes").split(','):
    markup_file_suffixes.add(suffix.strip())

port = config.getint("markupserve", "port")

debug(True)

run(host='localhost', port=port)
