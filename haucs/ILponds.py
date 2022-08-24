from haucs.utils.utils import coord2arr
import numpy as np
import pickle

coords = np.loadtxt('./ponds.txt')
arr, lat_range, long_range = coord2arr(coords)
np.savetxt('ILnormcoords.txt',arr,delimiter=',',fmt='%f')


# HPP, depot is the first point
with open('HPProutes.pkl','rb') as routes:
    all_routes = pickle.load(routes)
    all_routes = all_routes.squeeze()

ind = np.where(all_routes == 0)[0]
solved_routes = np.split(all_routes,ind)[1:-1]

for i, route in enumerate(solved_routes):
    final_route = coords[route,:] 
    np.savetxt('./routes'+str(i)+'.txt',final_route,delimiter=',',fmt='%f')