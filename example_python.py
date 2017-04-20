from haversine import haversine # latitude and longitude
from pysal.cg.kdtree import KDTree 
from pysal.cg.sphere import RADIUS_EARTH_KM
import numpy

coords = numpy.array([[12.968987, 77.590338],
    [12.969635, 77.591068],
    [12.9532701,77.5712036],
    [12.965430, 77.592511],
    [12.965033,77.5909873]])

tree = KDTree(coords, leafsize=10, radius=RADIUS_EARTH_KM)
# get points from KDTree
toQuery = (coords[0])
d,i = tree.query(toQuery, k=4, distance_upper_bound=0.005)
print d*100000,i,coords[0]
'''
for entry in i:
    if (entry >= len(coords)):
        break
    print(str(toQuery) + " to " + str(coords[entry]) + " = " +
        str(haversine(toQuery, (coords[entry]))) +
        " km")'''