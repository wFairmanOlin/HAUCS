from haucs.data.dataset import PondsDataset
# from haucs.utils.utils import coord2arr
import pickle
# import matplotlib.pyplot as plt
# import scipy.io as sio 
import numpy as np

# if __name__ == "__main__":
    
#     coords = np.loadtxt('C:\\Users\\coral-computer\\Documents\\github\\HAUCS\\haucs\\ponds.txt')
#     ILponds, lat_range, long_range = coord2arr(coords)
#     np.savetxt('C:\\Users\\coral-computer\\Documents\\github\\HAUCS\\haucs\\ILnormcoordsmall.txt',ILponds,delimiter=',',fmt='%f')
#     # ILponds = np.loadtxt('C:\\Users\\anthonydavis2020\\Documents\\github\\HAUCS\\haucs\\ILnormcoordsmall.txt', delimiter=',')

#     data = PondsDataset(farms=1, num_pts=5, xlims=[0, 1], ylims=[0, 1])
#     data.data = ILponds
    
#     sized_ATSP_ds = data.load_ATSP_dataset()
#     with open('C:\\Users\\coral-computer\\Documents\\github\\HAUCS\\haucs\\ATSP_IL.pkl', 'wb') as f:
#         pickle.dump(sized_ATSP_ds, f, pickle.HIGHEST_PROTOCOL)
    
#     GLOP = data.load_GLOP_dataset()
#     with open('C:\\Users\\coral-computer\\Documents\\github\\HAUCS\\haucs\\GLOP_dataset_IL.pkl', 'wb') as f:
#         pickle.dump(GLOP, f, pickle.HIGHEST_PROTOCOL)

    # HPP data written in matlab in solvers/HPP
    
def load(method:str, norm_coords:np.ndarray, output_path:str) -> None:
    """
    Load normalized pond data from a file and return a pickled dataset object
    """
    data = PondsDataset(farms=1, num_pts=5, xlims=[0, 1], ylims=[0, 1])
    data.data = norm_coords
    
    match method:
        case 'ATSP':
            sized_ATSP_ds = data.load_ATSP_dataset()
            with open(output_path, 'wb') as f:
                pickle.dump(sized_ATSP_ds, f, pickle.HIGHEST_PROTOCOL)

        case 'GLOP':
            GLOP = data.load_GLOP_dataset()
            with open(output_path, 'wb') as f:
                pickle.dump(GLOP, f, pickle.HIGHEST_PROTOCOL)

        case 'HPP':
            raise NotImplementedError
        case _:
            raise ValueError(f"Invalid method: {method}")