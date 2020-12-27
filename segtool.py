import tkinter
import pandas as pd
from PIL import Image, ImageTk
from tkinter import Tk, BOTH
from tkinter import Frame, Button, RAISED, SUNKEN, ROUND, TRUE
from functools import partial
#import pdb; pdb.set_trace()
#from tkinter.Tk import Style
import cv2
import os
import time
import itertools
import sys
import argparse
IMAGE_RESIZE_FACTOR = .3

class AppWindow(Frame):
    def __init__(self, parent, category_file, photo_folder, destination_folder):
        Frame.__init__(self, parent)
        self.category_file = category_file
        self.photo_folder = photo_folder
        self.destination_folder = destination_folder
        self.parent = parent
        self.buttonset = {}
        self.pixel_labels = {}
        self.frame = tkinter.Toplevel()
        self.__generate_buttons__()
        self.loadImage()
        self.initUI()
    def __generate_buttons__(self):
        labels = pd.read_csv(self.category_file)
        colors = itertools.cycle(["black", "red", "green", "blue", "cyan", "yellow", "magenta"])
        self.labels = list(labels['label'])
        for idx, label in enumerate(self.labels):
            action = partial(self.activate_button, label=label)
            color = next(colors)
            self.buttonset[label] =  Button(self.frame, text=label, fg=color, highlightbackground=color, command=action)
            self.buttonset[label].grid(row=idx, column=0)
            self.pixel_labels[label] = []
    def loadImage(self):
        img = cv2.imread("/Users/timothyelser/Downloads/IMG_0714.jpg")
        img = cv2.resize(img, (0,0), fx = IMAGE_RESIZE_FACTOR, fy = IMAGE_RESIZE_FACTOR)
        b, g, r = cv2.split(img)
        img = cv2.merge((r,g,b))
        im = Image.fromarray(img)
        self.image = ImageTk.PhotoImage(image=im)       
    def paint(self, event):

        self.buttonset[self.active_button].config(relief=SUNKEN)
        self.line_width = 5
#        print(self.buttonset[self.active_button].cget('highlightbackground'))
        paint_color =  self.buttonset[self.active_button].cget('highlightbackground')
        if self.old_x and self.old_y:
            self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,
                               width=self.line_width, fill=paint_color,
                               capstyle=ROUND, smooth=TRUE, splinesteps=36)

        self.pixel_labels[self.active_button].append([event.x, event.y])
        self.old_x = event.x
        self.old_y = event.y
        
    def activate_button(self, label):
        self.buttonset[self.active_button].config(relief=RAISED)
        self.buttonset[label].config(relief=SUNKEN)
        self.active_button = label
        print(self.pixel_labels[label])
        
    def initUI(self):
#        self.style = Style()
#        self.style.theme_use("default")
        self.old_x = None
        self.old_y = None
        self.active_button = self.labels[0]
        self.pack(fill=BOTH, expand=1)
        self.canvas = tkinter.Canvas(self, width = self.image.width(), height = self.image.height())
#        self.canvas = tkinter.Canvas(self, width = 2000, height = 2000)

        self.canvas.pack()
        self.canvas.create_image(0, 0, image=self.image, anchor="nw")
        self.canvas.bind('<B1-Motion>', self.paint)
        self.canvas.bind('<ButtonRelease-1>', self.reset)
    def reset(self, event):
        self.old_x = None
        self.old_y = None

def main(args, parsed):
    root = Tk()
#    root.geometry("250x150+300+300")
    app = AppWindow(root, parsed.category_file, parsed.photo_folder, parsed.destination_folder)
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='specify label options, photo_folder, destination_folder')
    parser.add_argument("--category_file", type=str)
    parser.add_argument("--photo_folder", type=str, default=None)
    parser.add_argument("--destination_folder", type=str, default=None)
    parsed = parser.parse_args()
    main(parser,  parsed)
