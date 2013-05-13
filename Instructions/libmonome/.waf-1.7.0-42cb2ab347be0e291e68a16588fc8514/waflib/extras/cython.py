#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
import waflib
import waflib.Logs as _msg
from waflib import Task
from waflib.TaskGen import extension,feature,before_method,after_method
cy_api_pat=re.compile(r'\s*?cdef\s*?(public|api)\w*')
re_cyt=re.compile(r"""
	(?:from\s+(\w+)\s+)?   # optionally match "from foo" and capture foo
	c?import\s(\w+|[*])    # require "import bar" and capture bar
	""",re.M|re.VERBOSE)
@extension('.pyx')
def add_cython_file(self,node):
	ext='.c'
	if'cxx'in self.features:
		self.env.append_unique('CYTHONFLAGS','--cplus')
		ext='.cc'
	for x in getattr(self,'cython_includes',[]):
		d=self.path.find_dir(x)
		if d:
			self.env.append_unique('CYTHONFLAGS','-I%s'%d.abspath())
	tsk=self.create_task('cython',node,node.change_ext(ext))
	self.source+=tsk.outputs
class cython(Task.Task):
	run_str='${CYTHON} ${CYTHONFLAGS} -o ${TGT[0].abspath()} ${SRC}'
	color='GREEN'
	vars=['INCLUDES']
	ext_out=['.h']
	def runnable_status(self):
		ret=super(cython,self).runnable_status()
		if ret==Task.ASK_LATER:
			return ret
		for x in self.generator.bld.raw_deps[self.uid()]:
			if x.startswith('header:'):
				self.outputs.append(self.inputs[0].parent.find_or_declare(x.replace('header:','')))
		return super(cython,self).runnable_status()
	def scan(self):
		txt=self.inputs[0].read()
		mods=[]
		for m in re_cyt.finditer(txt):
			if m.group(1):
				mods.append(m.group(1))
			else:
				mods.append(m.group(2))
		_msg.debug("cython: mods %r"%mods)
		incs=getattr(self.generator,'cython_includes',[])
		incs=[self.generator.path.find_dir(x)for x in incs]
		incs.append(self.inputs[0].parent)
		found=[]
		missing=[]
		for x in mods:
			for y in incs:
				k=y.find_resource(x+'.pxd')
				if k:
					found.append(k)
					break
			else:
				missing.append(x)
		_msg.debug("cython: found %r"%found)
		has_api=False
		has_public=False
		for l in txt.splitlines():
			if cy_api_pat.match(l):
				if' api 'in l:
					has_api=True
				if' public 'in l:
					has_public=True
		name=self.inputs[0].name.replace('.pyx','')
		if has_api:
			missing.append('header:%s_api.h'%name)
		if has_public:
			missing.append('header:%s.h'%name)
		return(found,missing)
def options(ctx):
	ctx.add_option('--cython-flags',action='store',default='',help='space separated list of flags to pass to cython')
def configure(ctx):
	if not ctx.env.CC and not ctx.env.CXX:
		ctx.fatal('Load a C/C++ compiler first')
	if not ctx.env.PYTHON:
		ctx.fatal('Load the python tool first!')
	ctx.find_program('cython',var='CYTHON')
	if ctx.options.cython_flags:
		ctx.env.CYTHONFLAGS=ctx.options.cython_flags