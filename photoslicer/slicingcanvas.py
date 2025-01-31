import tkinter as tk
import PIL
from PIL import ImageTk
from PIL import Image
from shapely.geometry import Polygon
import numpy as np


def slice_corner_tag(s, c):
    return "crn_" + str(s) + "x" + str(c)


def get_slice_and_corner_from_tags(tags):
    tag = next(filter(lambda x: x.startswith('crn_'), tags))
    sc = tag.split("_")[1].split("x")
    s = int(sc[0])
    c = int(sc[1])
    return s, c


def slice_edge_tag(s, e):
    return "edg_" + str(s) + "x" + str(e)


def get_slice_and_edge_from_tags(tags):
    tag = next(filter(lambda x: x.startswith('edg_'), tags))
    se = tag.split("_")[1].split("x")
    s = int(se[0])
    e = int(se[1])
    return s, e


def slice_tag(s):
    return "slice_" + str(s)


def slice_label_tag(s):
    return "lbl_" + str(s)


def get_slice_from_tags(tags):
    tag = next(filter(lambda x: x.startswith('lbl_'), tags))
    return tag.split("_")[1]


def polys_iou(poly1, poly2):
    poly_1 = Polygon(poly1)
    poly_2 = Polygon(poly2)
    iou = poly_1.intersection(poly_2).area / poly_1.union(poly_2).area
    return iou


class PhotoSlice:
    def __init__(self, bbox=None):
        if bbox is None:
            self.bbox = np.array([[10, 10], [800, 10], [800, 800], [10, 800]]).reshape(4, 2)
        else:
            self.bbox = bbox

        self.locked = False

    def toggle_locked(self, locked=None):
        if locked is not None:
            self.locked = locked
        else:
            self.locked = not self.locked

    def set_top_left_from_edge_index(self, i):
        # bbox = []
        # for n in range(4):
        #     j = (i + n) % 4
        #     bbox.append(self.bbox[j])
        #
        # self.bbox = np.array(bbox)
        self.bbox = np.roll(self.bbox, -i, axis=0)

    def update_corner(self, ci, x, y):
        self.bbox[ci][0] = x
        self.bbox[ci][1] = y


class SlicingCanvas(tk.Canvas):

    def enable(self, state='normal'):

        def set_status(widget):
            if widget.winfo_children:
                for child in widget.winfo_children():
                    child['state'] = state
                    set_status(child)

        set_status(self)

    def disable(self):
        self.enable('disabled')

    def __init__(self, parent, **kwargs):
        tk.Canvas.__init__(self, parent, **kwargs, borderwidth=0, highlightthickness=0, bg="black")
        self.zoom = 1.0
        self.image = None
        self.image_viewport = None
        self.picture_frame = None
        self.cross = [-1, -1, 8, -1, 8, 1, -8, 1, -8, -1, -1, -1, -1, -8, 1, -8, 1, 8, -1, 8]
        self.origin = [0, 0]
        self._on_bbox_updated = None
        self.slices = []

        # Events
        self.bind('<Configure>', self.update_view)
        self.bind('<ButtonPress-3>', self.view_drag_start)
        self.bind('<B3-Motion>', self.view_drag)
        self.bind('<ButtonRelease-3>', self.view_drag_stop)
        self.bind('<MouseWheel>', self.mouse_wheel)
        self.bind('<Button-5>', self.mouse_wheel)
        self.bind('<Button-4>', self.mouse_wheel)

        self.tag_bind("corner", "<ButtonPress-1>", self.corner_drag_start)
        self.tag_bind("corner", "<B1-Motion>", self.corner_drag)
        self.tag_bind("corner", "<ButtonRelease-1>", self.corner_drag_stop)

        self.tag_bind("edge", "<ButtonPress-1>", self.edge_select_top)
        self.tag_bind("label", "<ButtonPress-1>", self.label_lock_slice)

        self.corner_dragging_buffer = {"x": 0, "y": 0, "item": None}
        self.view_dragging_buffer = {"x": 0, "y": 0}

    def set_on_bbox_updated(self, fn):
        self._on_bbox_updated = fn

    def set_image(self, image, new_image=False):
        if self.image is None or new_image:
            self.zoom = self._get_zoom_automatic(image)
            self.xview_moveto(0)
            self.yview_moveto(0)
            #self.zoom = 1.0
            self.delete("frame")
            #self.picture_frame = self.create_rectangle(0, 0, image.width, image.height, outline="", tags=("frame",))
            self.picture_frame = self.create_rectangle(0, 0, image.width*self.zoom, image.height*self.zoom, outline="", tags=("frame",))
            self.slices = []
        self.image = image

    def _get_zoom_automatic(self, image):
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        return min( canvas_width/ image.width , canvas_height/ image.height )


    def add_bbox(self, bbx):
        self.slices.append(bbx)
        self.delete("slice")
        for b in range(len(self.slices)):
            self.__draw_slice(b)

        self.update_view()

    def update_bboxes(self, bbxs=None):
        if bbxs is not None:
            merged_slices = []
            for sl in self.slices:
                if sl.locked:
                    merged_slices.append(sl)

            for box in bbxs:
                # Check if bbox is the same as one of the locked slices
                overlaps_locked = False
                for sl in merged_slices:
                    if polys_iou(box, sl.bbox) > 0.3:
                        overlaps_locked = True
                        break
                if not overlaps_locked:
                    s = PhotoSlice(box)
                    merged_slices.append(s)

            self.slices = merged_slices

        self.delete("slice")
        for b in range(len(self.slices)):
            self.__draw_slice(b)

        self.update_view()

    def view_drag_start(self, event):
        self.scan_mark(event.x, event.y)
        self.view_dragging_buffer["x"] = event.x
        self.view_dragging_buffer["y"] = event.y

    def view_drag(self, event):
        self.scan_dragto(event.x, event.y, gain=1)
        self.update_view()  # redraw the image

    def view_drag_stop(self, event):
        self.scan_dragto(event.x, event.y, gain=1)
        self.origin[0] += event.x - self.view_dragging_buffer["x"]
        self.origin[1] += event.y - self.view_dragging_buffer["y"]

    def mouse_wheel(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        # Zoom only when pointer over image
        bbox = self.bbox(self.picture_frame)
        if not (bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]):
            return

        scale = 1.00
        delta = 1.05

        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120 or event.delta == 1:  # scroll down
            if self.zoom < 0.01:
                return

            self.zoom /= delta
            scale /= delta

        if event.num == 4 or event.delta == 120 or event.delta == -1:  # scroll up
            if self.zoom > 20:
                return
            self.zoom *= delta
            scale *= delta

        self.scale('all', 0, 0, scale, scale)
        self.update_view(x, y)

    def corner_drag_start(self, event):
        self.corner_dragging_buffer["item"] = self.find_withtag(tk.CURRENT)
        self.corner_dragging_buffer["x"] = event.x
        self.corner_dragging_buffer["y"] = event.y

    def corner_drag(self, event):
        delta_x = event.x - self.corner_dragging_buffer["x"]
        delta_y = event.y - self.corner_dragging_buffer["y"]
        self.move(self.corner_dragging_buffer["item"], delta_x, delta_y)
        self.corner_dragging_buffer["x"] = event.x
        self.corner_dragging_buffer["y"] = event.y

    def corner_drag_stop(self, event):
        tags = self.gettags(self.corner_dragging_buffer["item"])
        b, c = get_slice_and_corner_from_tags(tags)

        # Update bbox coords
        x = self.coords(self.corner_dragging_buffer["item"])[0] + 1
        y = self.coords(self.corner_dragging_buffer["item"])[1] + 1

        x /= self.zoom
        y /= self.zoom

        self.slices[b].update_corner(c, x, y)
        self.__draw_slice(b)

    def edge_select_top(self, event):
        line = self.find_withtag("current")[0]
        si, e = get_slice_and_edge_from_tags(self.gettags(line))
        self.slices[si].set_top_left_from_edge_index(e)
        self.slices[si].toggle_locked(True)
        self.__draw_slice(si)

    def label_lock_slice(self, event):
        label = self.find_withtag("current")[0]
        s = get_slice_from_tags(self.gettags(label))
        self.slices[int(s)].toggle_locked()
        self.update_bboxes()

    def __draw_slice(self, si):
        s = self.slices[si]
        s_tag = slice_tag(si)
        self.delete(s_tag)

        # Generates edge list
        edges = []
        prev = None
        origin = None
        for p in s.bbox:
            if prev is None:
                prev = p
                origin = p
                continue
            edge = (prev, p)
            edges.append(edge)
            prev = p
        edge = (prev, origin)
        edges.append(edge)

        # Draw edges
        for i, e in enumerate(edges):
            (a, b) = e
            if i == 0:
                color = "red"
            else:
                if s.locked:
                    color = "blue"
                else:
                    color = "lightgreen"

            self.create_line(a[0] * self.zoom, a[1] * self.zoom, b[0] * self.zoom, b[1] * self.zoom,
                             fill=color, width=3, tags=(s_tag, slice_edge_tag(si, i), "edge", "slice"))

        # Draw a "cross" at every corner of the bbox
        for i, p in enumerate(s.bbox):
            poly = self.create_polygon(self.cross, outline="blue", activeoutline="red",
                                       fill="gray", stipple='gray12', width=3,
                                       tags=(s_tag, slice_corner_tag(si, i), "corner", "slice"))
            self.move(poly, p[0], p[1])
            self.scale(poly, 0, 0, self.zoom, self.zoom)

        # Draw label
        center = Polygon(s.bbox).centroid.coords[:]
        if s.locked:
            color = "blue"
        else:
            color = "lightgreen"

        label = self.create_text(center, fill=color, text=str(si), font=('Arial', 20), activefill="red",
                                 tags=(s_tag, slice_label_tag(si), "label", "slice"))
        self.scale(label, 0, 0, self.zoom, self.zoom)
        self.tag_raise("corner")

    def update_view(self, x=0, y=0):
        if self.image is None:
            return

        pic_bbx = self.bbox(self.picture_frame)
        pic_bbx = (pic_bbx[0] + 1, pic_bbx[1] + 1, pic_bbx[2] - 1, pic_bbx[3] - 1)
        canvas_bbx = (self.canvasx(0),
                      self.canvasy(0),
                      self.canvasx(self.winfo_width()),
                      self.canvasy(self.winfo_height()))

        x1 = max(canvas_bbx[0] - pic_bbx[0], 0)
        y1 = max(canvas_bbx[1] - pic_bbx[1], 0)
        x2 = min(canvas_bbx[2], pic_bbx[2]) - pic_bbx[0]
        y2 = min(canvas_bbx[3], pic_bbx[3]) - pic_bbx[1]

        if int(x2 - x1) <= 0 or int(y2 - y1) <= 0:
            return

        x = min(int(x2 / self.zoom), self.image.width)
        y = min(int(y2 / self.zoom), self.image.height)

        image = self.image.crop((int(x1 / self.zoom), int(y1 / self.zoom), x, y))
        self.image_viewport = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1))))
        canvas_image = self.create_image(max(canvas_bbx[0], pic_bbx[0]), max(canvas_bbx[1], pic_bbx[1]),
                                         anchor='nw', image=self.image_viewport)
        self.lower(canvas_image)
