import tkinter
import json
import datetime
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


class Annotator:
    def __init__(self, config_json, existing_annotations=None):
        self.config_json = config_json
        self.annotations = {}
        self.annotation_id = 0
        self.labels = self.config_json['categories']
        self.photo_folder = self.config_json['photo_folder']
        self.images = {}
        if not existing_annotations:
            self.build_imagelist()
        self.build_labelist()
        self.annotation_boilerplate()
        
    def build_imagelist(self):
        self.image_list = []
        self.img_idx=0
        for idx, file_ in enumerate(os.listdir(self.photo_folder)):
            self.images[os.path.join(self.photo_folder,file_)] = idx
            self.image_list.append(os.path.join(self.photo_folder, file_))
        self.n_images = len(self.image_list)

    def build_labelist(self):
        labels = self.labels
        colors = itertools.cycle(["black", "red", "green", "blue", "cyan", "yellow", "magenta"])
        self.labelmap = {}
        self.inverse_labelmap = {}
        self.colormap = {}
        for idx, label in enumerate(self.labels):
            self.labelmap[idx] = label
            self.inverse_labelmap[label] = idx
            color = next(colors)
            self.colormap[label] = color

    def annotation_boilerplate(self):
        self.cocodata = {}
        self.__coco_info__()
        self.__coco_licenses__()
        self.__coco_images__()
        self.__coco_categories__()
        
    def __coco_info__(self):
        self.cocodata['info'] = {}
        self.cocodata['info']['description'] = self.config_json['description']
        self.cocodata['info']['version'] = self.config_json['version']
        self.cocodata['info']['date_created'] = datetime.datetime.now().strftime("%Y-%m-%d")

    def __coco_licenses__(self):
        self.cocodata['licenses'] = {}

    def __coco_categories__(self):
        self.cocodata['categories'] = []
        for key, value in self.labelmap.items():
            self.cocodata['categories'].append({"category": value, "id": key, "supercategory": value})

    def __coco_images__(self):
        self.cocodata['images'] = []
        for file_, idx in self.images.items():
            self.cocodata['images'].append({"license": 1, "filename": file_, "id": idx, "width": self.config_json['width'], "height": self.config_json['height'],
                                            "date_captured": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    def __coco_annotations__(self):
        self.cocodata['annotations'] = []
        counter = 0
        for file_, annotation_ in self.annotations.items():
            for label, polygons in annotation_.polygons.items():
                for polygon in polygons:
                    poly = polygon.simplify(1.0, preserve_topology=False)
                    segmentation = np.array(poly.exterior.coords).ravel().tolist()
                    x, y, max_x, max_y = poly.bounds
                    width = max_x - x
                    height = max_y - y
                    bbox = (x, y, width, height)
                    area = poly.area
                
                    self.cocodata['annotations'].append({"segmentation": segmentation,
                                                     "iscrowd": 0,
                                                     "image_id": self.images[file_],
                                                     "category_id": self.inverse_labelmap[label],
                                                     "id": counter,
                                                     "bbox": bbox,
                                                     "area": area
                                                     }
                                                    )
                    counter += 1
        with open(self.config_json['destination_file'], 'w') as file_:
            json.dump(self.cocodata, file_) 
        return
class annotation:
    def __init__(self, filename, labels):
        self.filename = filename
        self.polygons = {}
        for label in labels:
            self.polygons[label] = []
        self.vertices = []
        return
    
    
class AppWindow(Frame):
    def __init__(self, parent, config_file):
        Frame.__init__(self, parent)
        self.annotator = Annotator(config_file)
        self.width = config_file['width']
        self.height = config_file['height']
        self.parent = parent
        self.buttonset = {}
        self.frame = tkinter.Toplevel()
        self.__generate_buttons__()
        self.parent.bind("<Return>", self.finish_segmentation)
        self.parent.bind("<Tab>", self.clean_vertex)
        self.frame.bind("<Return>", self.finish_segmentation)
        self.frame.bind("<Tab>", self.clean_vertex)
        self.parent.bind('<Left>', self.__prev_image__)
        self.parent.bind('<Right>', self.__next_image__)
        self.initUI()
        self.image_on_canvas = None
        self.img_session(self.annotator.image_list[self.annotator.img_idx])

    def __prev_image__(self, event):
        if self.annotator.img_idx!=0:
            self.__clean_canvas__()
            self.annotator.img_idx-=1
            self.img_session(self.annotator.image_list[self.annotator.img_idx])
            self.annotator.__coco_annotations__()

        return

    def __next_image__(self, event):
        if self.annotator.img_idx<=self.annotator.n_images:
            self.__clean_canvas__()
            self.annotator.img_idx += 1
            self.img_session(self.annotator.image_list[self.annotator.img_idx])
            self.annotator.__coco_annotations__()
        return

    def finish_segmentation(self, event):
        if self.active_button:
            self.activate_button(self.active_button)
            
    def __generate_buttons__(self):
        for idx, label in enumerate(self.annotator.labels):
            action = partial(self.activate_button, label=label)
            color = self.annotator.colormap[label]
            self.buttonset[label] =  Button(self.frame, text=label, fg=color, highlightbackground=color, command=action)
            self.buttonset[label].grid(row=idx, column=0)

    def img_session(self, filename_):
        #Create Canvas or delete old one
        #If existing, fill in existing annotations and populate draw lists
        #If not existing, seed draw lines and pixel_labs for each label.
        self.drawn_polygons = {}
        self.drawn_lines = {}
        self.vertices = []
        self.drawn_cache = []
        if filename_ not in self.annotator.annotations.keys():
            self.annotator.annotations[filename_] = annotation(filename_, self.annotator.labels)
        self.active_annotation=self.annotator.annotations[filename_]
        self.loadImage(self.active_annotation.filename)
        if not self.image_on_canvas:
            self.image_on_canvas = self.canvas.create_image(0, 0, image=self.image, anchor="nw")
        else:
            self.canvas.itemconfig(self.image_on_canvas, image = self.image)
        for label in self.annotator.labels:
            self.drawn_lines[label] = []
            self.drawn_polygons[label] = []
        try:
            self.annotator.annotations[filename_]
            for label, polygons in self.annotator.annotations[filename_].polygons.items():
                for polygon in polygons:
                    self.draw_segmentation_boundaries(polygon, label)
        except KeyError:
            pass

    def loadImage(self, img_file):
        img = cv2.imread(img_file)
        img = cv2.resize(img, (self.width, self.height))
        b, g, r = cv2.split(img)
        img = cv2.merge((r,g,b))
        im = Image.fromarray(img)
        self.image = ImageTk.PhotoImage(image=im)       

    def draw_segmentation_boundaries(self, polygon, label):
        self.line_width = 5
        paint_color =  self.annotator.colormap[label]
        coords = polygon.exterior.coords
        bounding_lines = []
        for s_vertex, d_vertex in zip(coords, coords[1:]):
            ln = self.canvas.create_line(s_vertex[0], s_vertex[1], d_vertex[0], d_vertex[1],
                               width=self.line_width, fill=paint_color,
                               capstyle=ROUND, smooth=TRUE, splinesteps=36)
            bounding_lines.append(ln)
        self.drawn_polygons[label].append(bounding_lines)

        
    def id_vertex(self, event):
        if self.active_button:
            ln = self.canvas.create_line(event.x, event.y,event.x,event.y, width=10,
                                    fill=self.buttonset[self.active_button].cget('highlightbackground'),
                                    capstyle=ROUND, smooth=TRUE, splinesteps=1)
            self.vertices.append([event.x, event.y])
            self.drawn_cache.append(ln)
        return

    def clean_vertex(self, event):
        if len(self.vertices) > 0:
            self.vertices.pop()
            ln = self.drawn_cache.pop()
            self.canvas.delete(ln)
        else:
            if self.active_button:
                label = self.active_button
                if len(self.drawn_lines[label]) > 0:
                    lines = self.drawn_lines[label].pop()
                    self.active_annotation.polygons[label].pop()
                    for ln in lines:
                        self.canvas.delete(ln)
                if len(self.drawn_polygons[label]) > 0:
                    polygon_lines = self.drawn_polygons[label].pop()
                    for ln in polygon_lines:
                        self.canvas.delete(ln)

    def __clean_canvas__(self):
        self.vertices = []
        for ln in self.drawn_cache:
            self.canvas.delete(ln)
        self.drawn_cache = []
        for key in self.drawn_polygons.keys():
            for lines in self.drawn_polygons[key]:
                for ln in lines:
                    self.canvas.delete(ln)
            self.drawn_polygons[key] = []
        for key in self.drawn_lines.keys():
            for lines in self.drawn_lines[key]:
                for ln in lines:
                    self.canvas.delete(ln)
            self.drawn_lines[key] = []

    def __record_segmentation__(self, label):
        if len(self.vertices) > 2:
            polygon = Polygon(self.vertices)
            self.active_annotation.polygons[label].append(polygon)
            self.drawn_lines[label].append(self.drawn_cache)
            self.draw_segmentation_boundaries(polygon, label)
#            poly = polygon.simplify(1.0, preserve_topology=False)
#            segmentation = np.array(poly.exterior.coords).ravel().tolist()
        self.vertices = []
        self.drawn_cache = []
        
    def activate_button(self, label):
        if self.active_button:
            self.buttonset[self.active_button].config(relief=RAISED)
            if label == self.active_button:
                self.__record_segmentation__(label)
            else:
                self.__record_segmentation__(self.active_button)
                self.active_button = label
        else:
            self.active_button = label  
        self.buttonset[label].config(relief=SUNKEN)
        return
        
    def initUI(self):
        self.active_button = None
        self.pack(fill=BOTH, expand=1)
        self.canvas = tkinter.Canvas(self, width = self.width, height = self.height)

        self.canvas.pack()
#        self.canvas.create_image(0, 0, image=self.image, anchor="nw")
        self.canvas.bind("<Button-1>", self.id_vertex)

def main(config_json):
    root = Tk()
    app = AppWindow(root, config_json)
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='specify label options, photo_folder, destination_folder')
    parser.add_argument("--config_file", type=str)
    parsed = parser.parse_args()
    with open(parsed.config_file, 'r') as json_:
        config_json = json.load(json_)
    main(config_json)
