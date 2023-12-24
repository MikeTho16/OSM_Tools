#!/usr/bin/python3
""" Reads in an OSM file of nodes (currently only works with nodes)
and divides it geographically such that no more than n nodes appear
in each file.
"""
from dataclasses import dataclass
from xml.etree import ElementTree
import argparse
import os

class QTNode():
    """ Represents a node in a quad tree, it contains either a list of
    OSM nodes, or pointers to four other QTNodes. 
    """
    def __init__(self, min_lat, max_lat, min_lon, max_lon, max_members):
        self.members = []
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.mid_lat = (min_lat+max_lat)/2
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.mid_lon = (min_lon+max_lon)/2
        self.max_members = max_members
        self.is_leaf = True
        self.lower_left = None
        self.lower_right = None
        self.upper_left = None
        self.upper_right = None

    def add(self, osm_node):
        """ Adds an OSM node to this QTNode. If this is a leaf QTNode, the OSM
        node gets added directly, if this QTNode points is not a leaf node, 
        and just points to other QTNodes (children), call this method in the 
        appropriate child QTNode.
        """
        if self.is_leaf:
            self.members.append(osm_node)
            if len(self.members) > self.max_members:
                self.split()
        else:
            self.add_2_child(osm_node)

    def add_2_child(self, osm_node):
        """ Adds the specified OSM node to the appropriate child QTNode of this
        QTNode.
        """
        if osm_node.lat >= self.mid_lat:
            if osm_node.lon >= self.mid_lon:
                self.upper_right.add(osm_node)
            else:
                self.upper_left.add(osm_node)
        else:
            if osm_node.lon >= self.mid_lon:
                self.lower_right.add(osm_node)
            else:
                self.lower_left.add(osm_node)

    def split(self):
        """ Splits this QTNode into four "sub-nodes."  Each of the sub-nodes represent
        one of the four corners of the area that this QTNode represents.
        """
        self.upper_left = QTNode((self.min_lat+self.max_lat)/2, self.max_lat,
                                   self.min_lon, (self.min_lon+self.max_lon)/2, self.max_members)
        self.lower_left = QTNode(self.min_lat, (self.max_lat+self.min_lat)/2,
                                   self.min_lon, (self.min_lon+self.max_lon)/2, self.max_members)
        self.upper_right = QTNode((self.min_lat+self.max_lat)/2, self.max_lat,
                                    (self.min_lon+self.max_lon)/2, self.max_lon, self.max_members)
        self.lower_right = QTNode(self.min_lat, (self.max_lat+self.min_lat)/2,
                                    (self.min_lon+self.max_lon)/2, self.max_lon, self.max_members)
        self.is_leaf = False
        self.mid_lat = (self.max_lat + self.min_lat)/2
        self.mid_lon = (self.max_lon + self.min_lon)/2
        for node in self.members:
            self.add_2_child(node)
        self.members.clear()

    def write_leaves(self, out_dir, file_name):
        """ If this QTNode contains OSM nodes, write them out to a file, otherwise,
        call this method for each of the four QT sub-nodes.
        """
        if self.is_leaf:
            # Only create a file if this leaf is not empty.
            if self.members:
                file_name = os.path.join(out_dir, file_name + ".osm")
                with open(file_name, "w", encoding='utf-8') as file_handle:
                    file_handle.write("<?xml version='1.0' encoding='UTF-8'?>\n"
                       "<osm version='0.6' upload='never' download='never' generator='JOSM'>\n")
                    for member in self.members:
                        file_handle.write(ElementTree.tostring(member.node).decode())
                    file_handle.write("</osm>")
                    #print(file_name + ' ' +str(len(self.members)))
        else:
            self.lower_left.write_leaves(out_dir, file_name + 'SW')
            self.lower_right.write_leaves(out_dir, file_name + 'SE')
            self.upper_left.write_leaves(out_dir, file_name + 'NW')
            self.upper_right.write_leaves(out_dir, file_name + 'NE')

@dataclass
class OsmNodeWrapper():
    """ Contains information about a single OSM node.  The node is stored
    as an ElementTree.Element (from XML).
    """
    lat: float
    lon: float
    node: ElementTree.Element

def main():
    """ Main function of program
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("in_file",
                        help="An .osm file containing nodes to split")
    parser.add_argument("out_dir", help="directory in which to write the output")
    parser.add_argument("max_nodes", help="maximum nodes per file", type=int)
    args = parser.parse_args()
    tree = ElementTree.parse(args.in_file)
    root = tree.getroot()
    quad_tree = QTNode(-90, 90, -180, 180, args.max_nodes)
    for child in root:
        if child.tag == 'node':
            lat = float(child.attrib['lat'])
            lon = float(child.attrib['lon'])
            node = OsmNodeWrapper(lat, lon, child)
            quad_tree.add(node)
    quad_tree.write_leaves(args.out_dir, 'root')

if __name__ == '__main__':
    main()
