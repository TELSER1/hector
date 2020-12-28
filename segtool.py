import tkinter
import pandas as pd
import numpy as np
from PIL import Image, ImageTk
from tkinter import Tk, BOTH
from tkinter import Frame, Button, RAISED, SUNKEN, ROUND, TRUE
from functools import partial
from shapely.geometry import Polygon
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
        self.annotations = []
        self.annotation_id=0
        self.category_file = category_file
        self.photo_folder = photo_folder
        self.destination_folder = destination_folder
        self.parent = parent
        self.buttonset = {}
        self.pixel_labels = {}
        self.drawn_lines = {}
        self.frame = tkinter.Toplevel()
        self.__generate_buttons_and_labels__()
        self.loadImage()
        self.initUI()
        self.vertices = []
        self.parent.bind("<Return>", self.finish_segmentation)
        self.parent.bind("<Tab>", self.clean_vertex)
        self.drawn_cache = []
        
    def finish_segmentation(self, event):
        if self.active_button:
            self.activate_button(self.active_button)
            
    def __generate_buttons_and_labels__(self):
        labels = pd.read_csv(self.category_file)
        colors = itertools.cycle(["black", "red", "green", "blue", "cyan", "yellow", "magenta"])
        self.labels = list(labels['label'])
        self.labelmap = {}
        for idx, label in enumerate(self.labels):
            self.labelmap[idx] = label
            action = partial(self.activate_button, label=label)
            color = next(colors)
            self.buttonset[label] =  Button(self.frame, text=label, fg=color, highlightbackground=color, command=action)
            self.buttonset[label].grid(row=idx, column=0)
            self.pixel_labels[label] = []
            self.drawn_lines[label] = []

    def loadImage(self):
        img = cv2.imread("/Users/timothyelser/Downloads/IMG_0714.jpg")
        img = cv2.resize(img, (0,0), fx = IMAGE_RESIZE_FACTOR, fy = IMAGE_RESIZE_FACTOR)
        b, g, r = cv2.split(img)
        img = cv2.merge((r,g,b))
        im = Image.fromarray(img)
        self.image = ImageTk.PhotoImage(image=im)       

    def draw_segmentation_boundaries(self, polygon):
        self.line_width = 5
        paint_color =  self.buttonset[self.active_button].cget('highlightbackground')
        coords = polygon.exterior.coords
        for s_vertex, d_vertex in zip(coords, coords[1:]):
            self.canvas.create_line(s_vertex[0], s_vertex[1], d_vertex[0], d_vertex[1],
                               width=self.line_width, fill=paint_color,
                               capstyle=ROUND, smooth=TRUE, splinesteps=36)
    def id_vertex(self, event):
        if self.active_button:
            ln = self.canvas.create_line(event.x, event.y,event.x,event.y, width=10,
                                    fill=self.buttonset[self.active_button].cget('highlightbackground'),
                                    capstyle=ROUND, smooth=TRUE, splinesteps=1)
            self.vertices.append([event.x, event.y])
            self.drawn_cache.append(ln)
        return

    def clean_vertex(self, event):
        if len(self.vertices)>0:
            self.vertices.pop()
            ln = self.drawn_cache.pop()
            self.canvas.delete(ln)
        else:
            if self.active_button:
                label = self.active_button
                if len(self.drawn_lines[label])>0:
                    lines = self.drawn_lines[label].pop()
                    self.pixel_labels[label].pop()
                    for ln in lines:
                        self.canvas.delete(ln)
                    
    def __record_segmentation__(self, label):
        if len(self.vertices) > 2:
            print("recording segmentation")
            polygon = Polygon(self.vertices)
            self.drawn_lines[label].append(self.drawn_cache)
            self.draw_segmentation_boundaries(polygon)
            poly = polygon.simplify(1.0, preserve_topology=False)
            segmentation = np.array(poly.exterior.coords).ravel().tolist()
            self.pixel_labels[label].append(polygon)

        self.vertices = []
        self.drawn_cache = []
        
    def activate_button(self, label):
        if self.active_button:
            self.buttonset[self.active_button].config(relief=RAISED)
            if label == self.active_button:
                self.__record_segmentation__(label)
                self.active_button = None
            else:
                self.__record_segmentation__(self.active_button)
                self.active_button = label
        else:
            self.active_button = label  
        self.buttonset[label].config(relief=SUNKEN)
        return
        
    def initUI(self):
        self.old_x = None
        self.old_y = None
        self.active_button = None
        self.pack(fill=BOTH, expand=1)
        self.canvas = tkinter.Canvas(self, width = self.image.width(), height = self.image.height())

        self.canvas.pack()
        self.canvas.create_image(0, 0, image=self.image, anchor="nw")
        self.canvas.bind("<Button-1>", self.id_vertex)

    def reset(self, event):
        self.old_x = None
        self.old_y = None

def main(args, parsed):
    root = Tk()
    app = AppWindow(root, parsed.category_file, parsed.photo_folder, parsed.destination_folder)
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='specify label options, photo_folder, destination_folder')
    parser.add_argument("--category_file", type=str)
    parser.add_argument("--photo_folder", type=str, default=None)
    parser.add_argument("--destination_folder", type=str, default=None)
    parsed = parser.parse_args()
    main(parser,  parsed)
