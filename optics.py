import csv
import math
import json
from haversine import haversine # latitude and longitude
from pysal.cg.kdtree import KDTree 
from pysal.cg.sphere import RADIUS_EARTH_KM
import pdb
import numpy
import sqlite3

locs = numpy.array([[12.9232842072,77.5934100151]])
class Point:
    
    def __init__(self, latitude, longitude):
        
        self.latitude = latitude
        self.longitude = longitude
        self.cd = None              # core distance
        self.rd = None              # reachability distance
        self.processed = False      # has this point been processed?
        
    # --------------------------------------------------------------------------
    # calculate the distance between any two points on earth
    # --------------------------------------------------------------------------
    
    def distance(self, point):
        
        # convert coordinates to radians
        
        p1_lat, p1_lon, p2_lat, p2_lon = [math.radians(c) for c in self.latitude, self.longitude, point.latitude, point.longitude]
        
        numerator = math.sqrt(
            math.pow(math.cos(p2_lat) * math.sin(p2_lon - p1_lon), 2) +
            math.pow(
                math.cos(p1_lat) * math.sin(p2_lat) -
                math.sin(p1_lat) * math.cos(p2_lat) *
                math.cos(p2_lon - p1_lon), 2))

        denominator = (
            math.sin(p1_lat) * math.sin(p2_lat) +
            math.cos(p1_lat) * math.cos(p2_lat) *
            math.cos(p2_lon - p1_lon))
        
        # convert distance from radians to meters
        # note: earth's radius ~ 6372800 meters
        
        return math.atan2(numerator, denominator) * 6372800
        
    # --------------------------------------------------------------------------
    # point as GeoJSON
    # --------------------------------------------------------------------------
        
    def to_geo_json_dict(self, properties=None):
        
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [
                    self.longitude,
                    self.latitude,
                ]
            },
            'properties': properties,
        }
 
    def __repr__(self):
        return '(%f, %f)' % (self.latitude, self.longitude)

################################################################################
# CLUSTER
################################################################################

class Cluster:
    
    def __init__(self, points):
        
        self.points = points
        
    # --------------------------------------------------------------------------
    # calculate the centroid for the cluster
    # --------------------------------------------------------------------------

    def centroid(self):
        
        return Point(sum([p.latitude for p in self.points])/len(self.points),
            sum([p.longitude for p in self.points])/len(self.points))
            
    # --------------------------------------------------------------------------
    # calculate the region (centroid, bounding radius) for the cluster
    # --------------------------------------------------------------------------
    
    def region(self):
        
        centroid = self.centroid()
        radius = reduce(lambda r, p: max(r, p.distance(centroid)), self.points)
        return centroid, radius
        
    # --------------------------------------------------------------------------
    # cluster as GeoJSON
    # --------------------------------------------------------------------------
        
    def to_geo_json_dict(self, user_properties=None):
        
        center, radius = self.region()
        properties = { 'radius': radius }
        if user_properties: properties.update(user_properties)
        
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [
                    center.longitude,
                    center.latitude,
                ]
            },
            'properties': properties,
        }

################################################################################
# OPTICS
################################################################################

class Optics:
    
    def __init__(self, points, max_radius, min_cluster_size):
        
        self.points = points
        self.max_radius = max_radius                # maximum radius to consider
        self.min_cluster_size = min_cluster_size    # minimum points in cluster
    
    # --------------------------------------------------------------------------
    # get ready for a clustering run
    # --------------------------------------------------------------------------
    
    def _setup(self):
        
        for p in self.points:
            p.rd = None
            p.processed = False
        self.unprocessed = [p for p in self.points]
        self.ordered = []

    # --------------------------------------------------------------------------
    # distance from a point to its nth neighbor (n = min_cluser_size)
    # --------------------------------------------------------------------------
    
    def _core_distance(self, point, neighbors):

        if point.cd is not None: return point.cd
        if len(neighbors) >= self.min_cluster_size - 1:
            sorted_neighbors = sorted([n.distance(point) for n in neighbors])
            point.cd = sorted_neighbors[self.min_cluster_size - 2]
            return point.cd
        
    # --------------------------------------------------------------------------
    # neighbors for a point within max_radius
    # --------------------------------------------------------------------------
    
    def _neighbors(self, point):
        tree = KDTree(locs, leafsize=10, radius=RADIUS_EARTH_KM)
        # get points from KDTree
        neb = []
        toQuery = ([point.latitude,point.longitude])
        d,i = tree.query(toQuery, k=5, distance_upper_bound=self.max_radius/100000.0)
        arr = i.tolist()
        arr.pop(0)
        for itera in arr:
            if(itera < len(locs)):
                neb.append(Point(locs[itera][0],locs[itera][1]))
    #        print itera
        #pdb.set_trace()
        return [p for p in self.points if p is not point and
            p.distance(point) <= self.max_radius]
            
    # --------------------------------------------------------------------------
    # mark a point as processed
    # --------------------------------------------------------------------------
        
    def _processed(self, point):
        #pdb.set_trace()
        point.processed = True
        if(point in self.unprocessed):
            self.unprocessed.remove(point)
        self.ordered.append(point)
    
    # --------------------------------------------------------------------------
    # update seeds if a smaller reachability distance is found
    # --------------------------------------------------------------------------

    def _update(self, neighbors, point, seeds):
        
        # for each of point's unprocessed neighbors n...

        for n in [n for n in neighbors if not n.processed]:
            
            # find new reachability distance new_rd
            # if rd is null, keep new_rd and add n to the seed list
            # otherwise if new_rd < old rd, update rd
            
            new_rd = max(point.cd, point.distance(n))
            if n.rd is None:
                n.rd = new_rd
                seeds.append(n)
            elif new_rd < n.rd:
                n.rd = new_rd
    
    # --------------------------------------------------------------------------
    # run the OPTICS algorithm
    # --------------------------------------------------------------------------

    def run(self):
        
        self._setup()
        
        # for each unprocessed point (p)...
        
        while self.unprocessed:
            point = self.unprocessed[0]
            
            # mark p as processed
            # find p's neighbors
            
            self._processed(point)
            point_neighbors = self._neighbors(point)

            # if p has a core_distance, i.e has min_cluster_size - 1 neighbors

            if self._core_distance(point, point_neighbors) is not None:
                
                # update reachability_distance for each unprocessed neighbor
                
                seeds = []
                self._update(point_neighbors, point, seeds)
                
                # as long as we have unprocessed neighbors...
                
                while(seeds):
                    
                    # find the neighbor n with smallest reachability distance
                    
                    seeds.sort(key=lambda n: n.rd)
                    n = seeds.pop(0)
                    
                    # mark n as processed
                    # find n's neighbors
                    
                    self._processed(n)
                    n_neighbors = self._neighbors(n)
                    
                    # if p has a core_distance...
                    
                    if self._core_distance(n, n_neighbors) is not None:
                        
                        # update reachability_distance for each of n's neighbors
                        
                        self._update(n_neighbors, n, seeds)
                        
        # when all points have been processed
        # return the ordered list

        return self.ordered
        
    # --------------------------------------------------------------------------
    
    def cluster(self, cluster_threshold):
        
        clusters = []
        separators = []

        for i in range(len(self.ordered)):
            this_i = i
            next_i = i + 1
            this_p = self.ordered[i]
            this_rd = this_p.rd if this_p.rd else float('infinity')
            
            # use an upper limit to separate the clusters
            
            if this_rd > cluster_threshold:
                separators.append(this_i)

        separators.append(len(self.ordered))

        for i in range(len(separators) - 1):
            start = separators[i]
            end = separators[i + 1]
            if end - start >= self.min_cluster_size:
                clusters.append(Cluster(self.ordered[start:end]))

        return clusters

# LOAD SOME POINTS

points = []
with open('Jayanagar.csv') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        points.append(Point(float(row[0]),float(row[1])))
        lat = float(row[0])
        longi = float(row[1])
        locs = numpy.concatenate((locs,numpy.array([[lat,longi]])))
with open('Basavangudi.csv') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        points.append(Point(float(row[0]),float(row[1])))
        lat = float(row[0])
        longi = float(row[1])
        locs = numpy.concatenate((locs,numpy.array([[lat,longi]])))
with open('Madivala.csv') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        points.append(Point(float(row[0]),float(row[1])))
        lat = float(row[0])
        longi = float(row[1])
        locs = numpy.concatenate((locs,numpy.array([[lat,longi]])))
with open('KSLayout.csv') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        points.append(Point(float(row[0]),float(row[1])))
        lat = float(row[0])
        longi = float(row[1])
        locs = numpy.concatenate((locs,numpy.array([[lat,longi]])))
#pdb.set_trace()
optics = Optics(points, 100, 3) # 100m radius for neighbor consideration, cluster size >= 2 points
optics.run()                    # run the algorithm
clusters = optics.cluster(50)   # 50m threshold for clustering
# for cluster in clusters:
#     for pts in cluster.points:
#       print str(pts.latitude)+','+str(pts.longitude)
#     print ""
# print len(clusters)
db1 = sqlite3.connect("clusters.db")
c = db1.cursor()
c.execute('''DROP TABLE IF EXISTS clusters''')
c.execute('''CREATE TABLE clusters(raduis real, lat real, longi real, points number)''')

for cluster in clusters:
    maxRadius = -1
    clusterCenterLati = 0.0
    clusterCenterLongi = 0.0
    for pt1 in cluster.points:
        for pt2 in cluster.points:
            thisRaduis = pt1.distance(pt2)
            if maxRadius < thisRaduis:
                maxRadius = thisRaduis
                clusterCenterLati = (pt1.latitude + pt2.latitude)/2.0
                clusterCenterLongi = (pt1.longitude + pt2.longitude)/2.0
    print str(maxRadius)+","+str(clusterCenterLati)+","+str(clusterCenterLongi)+","+str(len(cluster.points))
    c.execute("INSERT INTO clusters VALUES (?, ?, ?, ?);", (maxRadius,clusterCenterLati,clusterCenterLongi,len(cluster.points)))
# Save (commit) the changes
db1.commit()
c.execute('SELECT * FROM clusters')
print c.fetchone()
# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
db1.close()