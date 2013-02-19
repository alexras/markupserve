#!/usr/bin/env python

from bottle import run, debug, route, abort, redirect, request, static_file
import shlex
import collections
import whoosh
from whoosh.fields import SchemaClass
from whoosh import index
from whoosh.qparser import QueryParser
import ConfigParser
import os
import argparse
import jinja2
import subprocess
import shlex
import time
import calendar
import re
import pprint
import itertools
import datetime
import hashlib

DIR_CONFIG_FILE_NAME = ".markupserve_dir_config"
FILE_READ_BLOCK_SIZE = 2**20

config = ConfigParser.ConfigParser()

jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'),
                               trim_blocks = True)
markup_file_suffixes = set()

markupserve_index = None

class MarkupServeSchema(SchemaClass):
    path = whoosh.fields.ID(stored = True)
    title = whoosh.fields.TEXT(stored = True)
    content = whoosh.fields.TEXT(
        analyzer = (whoosh.analysis.StemmingAnalyzer()),
        stored = True)
    file_hash = whoosh.fields.ID(stored = True)

# From http://code.activestate.com/recipes/
# 466341-guaranteed-conversion-to-unicode-or-byte-string/
def safe_unicode(obj, *args):
    """ return the unicode representation of obj """
    try:
        return unicode(obj, *args)
    except UnicodeDecodeError:
        # obj is byte string
        ascii_text = str(obj).encode('string_escape')
        return unicode(ascii_text)

def find_program(program):
    for path in os.environ["PATH"].split(os.pathsep):
        executable = os.path.join(path, program)
        if os.path.exists(executable) and os.access(executable, os.X_OK):
            return os.path.abspath(executable)
    return None

def last_modified_string(file_path):
    return time.strftime("%Y/%m/%d %I:%M:%S %p", time.localtime(
            os.path.getmtime(file_path)))

def file_path_to_server_path(path, root):
    return os.path.join("/view", os.path.relpath(path, root))

def view_calendar(path, parent_path, root, config):
    files = os.listdir(path)

    try:
        file_prefix = config.get("style", "file_prefix").strip('"')
    except ConfigParser.Error:
        file_prefix = ""

    try:
        file_suffix = config.get("style", "file_suffix").strip('"')
    except ConfigParser.Error:
        file_suffix = ""

    filename_regex = re.compile("%s([0-9]+)-([0-9]+)-([0-9]+)%s" %
                                (file_prefix, file_suffix))

    def regex_match_function(x):
        match = filename_regex.match(x)

        if match is not None:
            return match.groups()
        else:
            return None

    file_dates = [match for match in map(regex_match_function, files)]

    files_by_month = {}

    for filename, date in itertools.izip(files, file_dates):
        if date is None:
            continue

        file_path = os.path.join(path, filename)
        year, month, day = map(int, date)
        date = datetime.date(year, month, day)

        year_and_month = (year, month)

        if year_and_month not in files_by_month:
            files_by_month[year_and_month] = {}

        files_by_month[year_and_month][date] = file_path

    calendars = {}

    cal = calendar.Calendar()
    # Render weeks beginning on Sunday
    cal.setfirstweekday(6)

    for year_and_month, dates in files_by_month.items():
        year, month = year_and_month

        if year not in calendars:
            calendars[year] = {}

        calendars[year][month] = []

        for week in cal.monthdatescalendar(year, month):
            week_list = []
            for date in week:
                date_info = {}

                if date in files_by_month[year_and_month]:
                    date_info["link"] = file_path_to_server_path(
                        files_by_month[year_and_month][date], root)

                date_info["day_of_month"] = date.day

                if date.month == month:
                    date_info["style_class"] = "cur_month_date"
                else:
                    date_info["style_class"] = "adjacent_month_date"

                week_list.append(date_info)

            calendars[year][month].append(week_list)

    template = jinja_env.get_template("calendar.jinja")

    return template.render(
        calendars = calendars,
        month_names = calendar.month_name,
        path = path,
        parent_path = file_path_to_server_path(parent_path, root))

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

        file_info["link"] = file_path_to_server_path(file_path, root)

        file_info["last_modified"] = last_modified_string(file_path)

        listable_files.append(file_info)

    if sorted_by is not None:
        listable_files.sort(key=lambda x: x[sorted_by], reverse = reverse)

    if parent_path != None:
        parent_path_info = {
            "name" : "Parent Directory",
            "link" : file_path_to_server_path(parent_path, root),
            "last_modified" : last_modified_string(parent_path),
            "icon" : "/static/up.png"
            }

        listable_files.insert(0, parent_path_info)

    template = jinja_env.get_template("dir.jinja")

    page_uri = file_path_to_server_path(path, root)

    return template.render(files = listable_files, path = path,
                           page_uri = page_uri, sorted_by = sorted_by,
                           reverse = reverse)

def view_file(path, root):
    file_suffix = os.path.splitext(path)[1]

    parent_dir = os.path.abspath(os.path.join(path, os.pardir))

    files_in_dir = filter(
        lambda x: os.path.splitext(x)[1] != ".resources" and x[0] != '.',
        os.listdir(parent_dir))

    files_in_dir.sort()

    file_index = files_in_dir.index(os.path.relpath(path, parent_dir))

    def make_path_struct(filename):
        path_dict = {
            "name" : os.path.splitext(filename)[0],
            "link" : '/'.join(("/view", os.path.relpath(parent_dir, root),
                               filename))
            }

        return path_dict

    if file_index > 0:
        prev_path = make_path_struct(files_in_dir[file_index - 1])
    else:
        prev_path = None

    if file_index < len(files_in_dir) - 1:
        next_path = make_path_struct(files_in_dir[file_index + 1])
    else:
        next_path = None

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

    parent_path = "/view/" + os.path.relpath(parent_dir, root)

    # Get rid of any Unicode garbage that Jinja might choke on
    output = output.decode("utf-8")

    return template.render(filename=filename, content=output,
                           parent=parent_path, prev=prev_path, next=next_path)

@route("/static/:filename")
def serve_static_file(filename):
    static_root = os.path.join(os.path.dirname(__file__), "static")

    return static_file(filename, root=static_root)

def grep_search(search_terms, document_root):
    command = shlex.split('grep -Hir "%s" %s' % (search_terms, document_root))

    grep_process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

    (output, error) = grep_process.communicate()

    if grep_process.returncode not in [0,1]:
        abort(500, "'%s' failed with error %d: %s %s" % (
                command, grep_process.returncode, output, error))

    results = collections.defaultdict(list)

    for match in output.split('\n'):
        if len(match) == 0:
            continue

        (filename, delim, line_text) = match.partition(':')

        file_extension = os.path.splitext(filename)[1]

        if file_extension not in markup_file_suffixes:
            continue

        filename = os.path.relpath(filename, document_root)
        results[filename].append(line_text)

    return results

def index_search(search_terms, document_root):
    qp = QueryParser("content", schema = markupserve_index.schema)
    query = qp.parse(safe_unicode(search_terms))

    results = collections.defaultdict(list)

    split_terms = shlex.split(search_terms)

    with markupserve_index.searcher() as searcher:
        query_results = searcher.search(query, limit=None)

        for result in query_results:
            filename = result["path"].decode("utf-8")
            results[filename].append(
                result.highlights("content").decode("utf-8"))

    return results

@route("/search")
def search():
    search_terms = request.GET.dict["terms"][0]

    document_root = os.path.expanduser(config.get(
            "markupserve", "document_root"))

    if markupserve_index is None:
        search_function = grep_search
    else:
        search_function = index_search

    results = search_function(search_terms, document_root)
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

        markupserve_dir_config_file = os.path.join(absolute_path,
                                                   DIR_CONFIG_FILE_NAME)

        if os.path.exists(markupserve_dir_config_file):
            dir_config = ConfigParser.ConfigParser()
            parsed_files = dir_config.read([markupserve_dir_config_file])

            if len(parsed_files) != 1:
                abort(500, "Can't parse dir config file '%s'" %
                      (markupserve_dir_config_file))

            try:
                dir_style = dir_config.get("style", "name")
            except ConfigParser.Error, e:
                abort(500, "Can't find option ('style', 'name') in directory "
                      "config")

            if dir_style == "calendar":
                return view_calendar(absolute_path, parent_path, document_root,
                                     dir_config)

        return view_dir(absolute_path, parent_path, document_root,
                        sorted_by, reverse)
    else:
        return view_file(absolute_path, document_root)

@route("/")
@route("/view/")
def view_index():
    return view("/")

def hash_file_contents(contents):
    return hashlib.md5(contents).hexdigest()

def build_index(writer):
    document_root = os.path.expanduser(config.get(
            "markupserve", "document_root"))

    for dirpath, dirnames, filenames in os.walk(document_root):
        for filename in filenames:
            filename_root, file_extension = os.path.splitext(filename)

            file_abspath = os.path.join(dirpath, filename)

            if file_extension not in markup_file_suffixes:
                continue

            with open(file_abspath, 'r') as fp:
                file_contents = fp.read()

            file_hash = hash_file_contents(file_contents)

            writer.add_document(
                title = safe_unicode(filename_root),
                content = safe_unicode(file_contents),
                file_hash = safe_unicode(file_hash),
                path = safe_unicode(
                    os.path.relpath(file_abspath, document_root)))

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

# Load an index file from index path if one has been specified
if config.has_option("markupserve", "index_root"):
    index_root = os.path.expanduser(config.get("markupserve", "index_root"))

    if os.path.isdir(index_root):
        print "Loading index at '%s'" % (index_root)
        # Index exists; load it
        markupserve_index = index.open_dir(index_root)
    else:
        # Index doesn't exist; create it
        print "Creating index at '%s'" % (index_root)

        os.makedirs(index_root)

        markupserve_index = index.create_in(
            index_root, MarkupServeSchema)

        print "Populating the index ..."
        try:
            writer = markupserve_index.writer()
            build_index(writer)
            writer.commit()
        except whoosh.store.LockError, e:
            print "Index is locked; aborting ..."

debug(True)

run(host='localhost', port=port)
