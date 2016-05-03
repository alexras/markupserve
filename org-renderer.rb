#!/usr/bin/env ruby

require 'rubygems'
require 'org-ruby'

filename = ARGV[0]

data = IO.read(filename)
puts Orgmode::Parser.new(data).to_html
