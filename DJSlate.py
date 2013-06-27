from kivy.app import App
from kivy.config import Config

#allow users to set fullscreen mode or not
fs = open('fullscreen.txt', 'r').read()
if fs.lower() == 'yes': Config.set('graphics', 'fullscreen', 'auto')
Config.set('kivy', 'window_icon', 'DJSlate.png') #set icon

from kivy.lang import Builder
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.graphics import Color, Line, Bezier
from kivy.uix.widget import Widget
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from mingus.core import notes, chords
from mingus.containers import *
from random import random
from math import ceil

from mingus.midi import fluidsynth
fluidsynth.init('fluid.sf2') #set soundfont

#initialize default settings
#these are changed by buttons
#so they are declared here globally
fluidsynth.set_instrument(1, 0)
octaveSet = 2
keySet = 'C'
scaleSet = 'Major'
notesChange = True #keep track of changes, so we don't have to recompute unnecessarily
allScales = {}
currentNotes = []

class SlateWidget(Widget):
	notesp = {} #contain playing notes
		
	def on_touch_down(self, touch):
		#draw pretty lines on screen, inspired by online demo
		color = (random(), random(), random())
		with self.canvas:
			Color(*color)
			touch.ud[touch.uid] = Line(points=(touch.x, touch.y), width=5)
			for pos in self.getNote(touch.x, self.width, True):
				Bezier(points=[int(round(float(pos)*float(self.width))), 0, int(round(float(pos)*float(self.width))), Window.height], group='grid', dash_offset=4)
		
		#add note to notesp {} and start playing, by touch.uid
		if touch.uid in self.notesp:
			fluidsynth.stop_Note(self.notesp[touch.uid], 1)
		self.notesp[touch.uid] = self.getNote(touch.x, self.width)
		fluidsynth.play_Note(self.notesp[touch.uid])
		
	def on_touch_move(self, touch):
		#add point to line, get new note for touch
		touch.ud[touch.uid].points += [touch.x, touch.y]
		newNote = self.getNote(touch.x, self.width)
		
		#if newNote isn't the same as what we saved
		#stop the note and start a new one
		if (newNote not in self.notesp.values()):
			fluidsynth.stop_Note(self.notesp[touch.uid], 1)
			self.notesp[touch.uid] = newNote
			fluidsynth.play_Note(self.notesp[touch.uid])
		
	def on_touch_up(self, touch):
		#delete the note and line on_touch_up
		try:
			if len(self.notesp) <= 1:
				self.canvas.remove_group('grid')
			self.canvas.remove(touch.ud[touch.uid])
			fluidsynth.stop_Note(self.notesp[touch.uid], 1)
			del self.notesp[touch.uid]
		except:
			pass
		
	#getNote based on x-position
	def getNote(self, x, width, rc = False):
		xratio = float(x)/float(width)
		sectors = self.getAllNotes()
		
		copy = [1]*len(sectors)
		for pos in xrange(len(copy)):
			copy[pos] = float((pos + 1))/float(len(copy))
		
		#if rc flag is true
		#return location ratio for note changes
		#used to draw grid lines
		if rc:
			return copy
				
		for pos in xrange(len(copy)):
			if xratio <= copy[pos]:
				return sectors[pos]
				
		#unnecessary
		return sectors[-1]

	#get possible notes
	#based on key/octave/scale
	def getAllNotes(self):
		global notesChange
		global octaveSet
		global keySet
		global scaleSet
		global allScales
		global currentNotes
	
		#don't recompute unnecessarily
		if notesChange == False:
			return currentNotes
		
		format = allScales[scaleSet][0]
		pitches = [i for i in allScales[scaleSet][1]] #array references...smh
		translate = {'S':'C', 'R1':'C#', 'R2':'D', 'G1':'D',
			'R3':'Eb', 'G2':'Eb', 'G3':'E', 'M1':'F', 
			'M2':'F#', 'P':'G', 'D1':'Ab', 'D2':'A', 
			'N1':'A', 'D3':'Bb', 'N2':'Bb', 'N3':'B'}
		
		#using translate dict, convert to western style
		if format == 'Carnatic':
			for i in xrange(len(pitches)):
				pitches[i] = translate[pitches[i]]
		
		#deal with Mingus and some MIDI stupidity/intelligence
		#where Note(Cb) does not return the same MIDI code as Note(B)
		pitches = [i.replace('Cb', 'B') for i in pitches]
		
		#figure out the transposition offset from C
		offset = int(Note(keySet)) - int(Note('C'))
		
		#calculate split point
		halfOctave = Note('G')
		halfOctave.octave_down()
		halfOctave = self.setOff(halfOctave, offset)
		
		#calculate trailing final note
		trailing = Note('C-5')
		trailing.octave_down()
		trailing = self.setOff(trailing, offset)
		
		for i in xrange(len(pitches)):
			pitches[i] = Note(pitches[i]) #octave = 4
			pitches[i].octave_down() #default is 3
			pitches[i] = self.setOff(pitches[i], offset) #transpose to key
		
		#spt is the octave split point (G in key of C)
		#if there's no natural split, just split the scale in half
		try:
			sPt = pitches.index(halfOctave)
		except ValueError:
			sPt = int(ceil(len(pitches)))
		
		#dammit, Python, with your object references
		fhalf = [Note(i) for i in pitches[:sPt]]
		shalf = [Note(i) for i in pitches[sPt:]]
		
		if octaveSet == 1:
			out = pitches + [trailing]
		
		elif octaveSet == 2:
			out = self.lower(shalf, 1) + pitches + self.higher(fhalf, 1)
			
		elif octaveSet == 3:
			out = self.lower(pitches, 1) + pitches + self.higher(pitches, 1) + self.higher([trailing], 1)
			
		elif octaveSet == 4:
			out = self.lower(shalf, 2) + self.lower(pitches, 1) + pitches + self.higher(pitches, 1) + self.higher(fhalf, 2)

		currentNotes = out
		notesChange = False
		return out
			
	def lower(self, pitches, amount):
		pitches = [Note(i) for i in pitches]
		for i in xrange(len(pitches)):
			pitches[i].change_octave(-amount)
		
		return pitches
		
	def higher(self, pitches, amount):
		pitches = [Note(i) for i in pitches]
		for i in xrange(len(pitches)):
			pitches[i].change_octave(+amount)
		
		return pitches
		
	def setOff(self, pitch, offset):
		return Note(int(pitch) + offset)
		
class DJSlate(App):
	title = 'DJ Slate'
	
	def build(self):
		global notesChange
		global octaveSet
		global keySet
		global scaleSet
		global allScales
		global currentNotes
		
		#the title that appears at the top
		header = Label(text='DJ Slate')
		
		#create binding function to set octave
		#create octave spinner, add four choices
		def setOctaves(spinner, oct):
			global notesChange
			global octaveSet
			octaveSet = int(oct.split(' ')[0]) #get N from 'N Octaves'
			notesChange = True
		
		octaves = Spinner(
			text = '2 Octaves', 
			values = ('1 Octave', '2 Octaves', '3 Octaves', '4 Octaves'),
			background_color = (1,1,1,0)
		)
		
		octaves.bind(text=setOctaves)
		
		#create setKey binding function
		#create key spinner, add keys
		def setKey(spinner, base):
			global notesChange
			global keySet
			keySet = base
			notesChange = True
		
		key = Spinner(
			text = 'C', 
			values = ('C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'),
			background_color = (1,1,1,0)
		)
		
		key.bind(text=setKey)
		
		#process midi.txt
		list = open('midi.txt').read()
		list = list.splitlines()
		instrumentNames = []
		
		#add instruments to spinner, bind select
		#number = 1, 2, 3, etc..
		#sound = Acoustic Grand Piano, etc...
		#instrumentNames[number-1] = sound
		for item in list:
			item = item.split(' ')
			number = int(item[0])
			sound = ' '.join(item[1:])
			instrumentNames.append(sound)
		
		instrument = Spinner(
			text = instrumentNames[0],
			values = tuple(instrumentNames),
			background_color = (1,1,1,0)
		)
		
		def setInstrument(spinner, inst):
			fluidsynth.set_instrument(1, instrumentNames.index(inst))
		
		instrument.bind(text=setInstrument)
		
		#process scales.txt
		list = open('scales.txt').read()
		list = list.splitlines()
		scaleNames = {}
		rawNames = [] #used to preserve name order
		
		#add scales to spinner, bind select
		#scaleNames[name_of_scale] = [type, notes]
		for item in list:
			item = item.split(' ')
			sname = item[0].replace('_',' ')
			type = item[1]
			notes = item[2:]
			rawNames.append(sname)
			scaleNames[sname] = [type, notes]
		
		scale = Spinner(
			text = 'Major',
			values = tuple(rawNames),
			background_color = (1,1,1,0)
		)
		
		def setScale(spinner, val):
			global notesChange
			global scaleSet
			scaleSet = val
			notesChange = True
		
		allScales = scaleNames
		scale.bind(text=setScale)
		
		#Create three parts of screen
		label = BoxLayout(size_hint=(1, .1))#, pos=(0, Window.height*.9))
		slate = SlateWidget(size_hint=(1, .8))#, pos=(0, Window.height*.2))
		buttons = BoxLayout(size_hint=(1, .1))#,  pos=(0, 0))
		
		#Add subsidiary buttons + slate
		buttons.add_widget(instrument)
		buttons.add_widget(scale)
		label.add_widget(octaves)
		label.add_widget(header)
		label.add_widget(key)
		
		#Add to window and return
		root = BoxLayout(orientation='vertical') #FloatLayout()
		root.add_widget(label)
		root.add_widget(slate)
		root.add_widget(buttons)
		
		'''def reposition(*args):
			labelMove = Animation(x=0, y=Window.height*.9, duration=0.1, t='instant')
			labelMove.start(label)
			
			slateMove = Animation(x=0, y=Window.height*.2, duration=0.1, t='instant')
			slateMove.start(slate)
		
		Window.bind(on_resize=reposition)'''
		
		return root

if __name__ == '__main__':
	DJSlate().run()