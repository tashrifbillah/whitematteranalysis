""" register.py

implementation of fiber tractography registration (group)

class RegisterTractographyNonlinear


"""

try:
    import scipy.optimize
    USE_SCIPY = 1
except ImportError:
    USE_SCIPY = 0
    print "<congeal.py> Failed to import  scipy.optimize, cannot align or register."
    print "<congeal.py> Please install  scipy.optimize for this functionality."

import numpy
import sys
import time
import vtk
try:
    from joblib import Parallel, delayed
    USE_PARALLEL = 1
except ImportError:
    USE_PARALLEL = 0
    print "<congeal.py> Failed to import joblib, cannot multiprocess."
    print "<congeal.py> Please install joblib for this functionality."

import whitematteranalysis as wma

class RegisterTractographyNonlinear(wma.register_two_subjects.RegisterTractography):

    def constraint(self, x_current):
        # Make sure the optimizer is searching in a reasonable region.
        # aim to preserve volume using the determinant of the overall affine transform
        affine_part = vtk.vtkLandmarkTransform()
        source_landmarks = convert_numpy_array_to_vtk_points(x_current)
        target_landmarks = convert_numpy_array_to_vtk_points(self.target_landmarks)
        affine_part.SetSourceLandmarks(source_landmarks)
        affine_part.SetTargetLandmarks(target_landmarks)
        affine_part.SetModeToAffine()
        affine_part.Update()
        det = affine_part.GetMatrix().Determinant()
        penalty = -100 * (1 - det)
        return penalty
    
    def __init__(self):
        # parameters that should be set by user
        self.sigma = 5
        self.process_id_string = ""
        self.output_directory = None
        
        # performance options that should be set by user
        self.verbose = False
        self.render = False
        
        # optimizer parameters that should be set by user
        self.maxfun = 300

        # output of registration
        self.objective_function_values = list()
        self.final_transform = None
        
        # subject data that must be input
        #self.fixed = None
        #self.moving = None
        #self.initial_step = 5
        #self.final_step = 2

        # set up default landmarks
        self.target_landmarks = list()
        self.nonlinear_grid_resolution = 3
        self.nonlinear_grid_3 = [-120, 0, 120]
        self.nonlinear_grid_4 = [-120, -60, 60, 120]
        self.nonlinear_grid_5 = [-120, -60, 0, 60, 120]
        self.nonlinear_grid_6 = [-120, -60, -20, 20, 60, 120]
        self.nonlinear_grid_8 = [-120, -85, -51, -17, 17, 51, 85, 120]
        self.nonlinear_grid_10 = [-120, -91, -65, -39, -13, 13, 39, 65, 91, 120]
        # random order so that optimizer does not start in one corner every time
        # the order was computed as
        # numpy.random.permutation(range(0,27))
        # numpy.random.permutation(range(0,64))
        # numpy.random.permutation(range(0,125))
        # numpy.random.permutation(range(0,216))
        self.grid_order_3 = [22,  8,  0, 14,  5, 19, 20,  9, 17, 15,  2, 11,  1, 12, 21,  6, 25, 7,  3, 24, 13, 18, 26, 16, 23,  4, 10]
        self.grid_order_4 = [58, 54,  4, 62, 51, 41, 52, 45, 59,  8, 29, 17, 61, 46, 18, 22, 34, 42, 21,  0,  3, 39, 27, 13, 60, 12,  2, 15,  5, 28,  7, 43, 31, 38, 33, 55,  1, 37, 47, 30, 24, 35, 14, 50, 20, 36, 44, 53, 16, 57, 56, 10, 48, 26,  6, 25,  9, 32, 19, 11, 63, 23, 49, 40]
        self.grid_order_5 = [ 75,  18,  54,  61,  64,  73,  95,  13, 111, 118,  43,   7,  46, 56,   4, 124,  77,  98,  72,  60,  38,  80,  36,  27, 120, 119, 51,  81,   0,  93,  11,  41,  69,  83, 107,  12, 106,  30,  53, 105,  33,  91,  28,  17,  58,  90,  45,  94,  14,  26,  84,   1, 92,  21,  47,  59, 100,   2,   3,  87,  65, 102,  68,  20,  85, 79,  82,  15,  32,  88, 115,  74,   6,  19,  35,  99, 104, 109, 70, 101,  96,  66,  52,  48,  49,  31,  97, 122,  78, 113,  55, 112,  76,  44,  23, 103,  16,  10, 123,  86,  39,   8,  62, 110, 42, 114,  40, 117,  63,   9,  25,  67,  71,  37,  24, 116,  57, 89, 121,  34,   5,  29, 108,  50,  22]
        self.grid_order_6 = [165,  63, 129, 170, 148, 131,   1, 205, 181,  69,  35, 100,   6, 13,  82, 193, 159, 130,  54, 164, 174,  62, 108, 101, 169,  93, 112,  42, 110, 213, 107,  47,  45, 140, 138, 199, 125, 117,   8, 41, 215,  74, 143, 155, 144, 187,  26,  60, 139,  58,  97,  10, 113,  34, 116,  33, 202, 210,  27, 135, 152, 206, 128,  16, 177, 25,  67, 192, 147, 132, 160, 158, 161,  90, 102,  49,  21, 191, 32,  18,  81, 157, 114, 175,  94, 172, 207, 186, 167, 163, 196, 118,  28,  43, 133, 171, 211,  77,  56, 195, 173,  57,  96,  29, 64, 180,  89, 190, 115,  20,  52,  50,   4, 141,  98, 134, 109, 149, 176, 212,  11,   0, 146,  65,  91,  23,  53,  44, 123,  87, 24, 178, 184,  68, 124,  46,  76, 151, 127, 204, 154, 150, 106, 70,  37,  84,  17,  12, 189,   2,  92,  36,  71,  39,  30,  75, 179, 168,  73, 121,  86, 214, 188,  59, 209,  22,  19, 153, 162, 99, 182,  14,  48, 119, 203,  66,  61, 103, 208, 145,  79,  85, 142,  72, 126, 194, 104, 122, 198, 120, 200, 183, 201,   3,  78, 40,  83, 137,  31, 111,  15,  51,   9, 185,  55,  38, 156, 136, 7,  95,  80, 105, 166,  88, 197,   5]
        self.grid_order_8 = [455, 240,  90,  94, 412,  27, 287, 423, 102,   2, 171, 220, 159, 56,   6, 233, 454,  33,  73, 180, 213, 205, 253, 294, 105, 202, 224, 474, 299, 460, 282, 432, 468, 121, 307, 112, 409, 420,  76,  7, 239, 217, 279, 103, 419,  58, 425, 152, 387, 111, 391, 293, 179, 471,  20, 310, 264,  63, 100,  65, 346, 510,  82, 257, 302, 47, 242, 490, 141, 232, 211, 356, 110, 284,  86, 336, 396, 352, 451,  30, 497, 192, 427, 361, 144, 417, 466, 331, 416, 193, 338, 128, 163, 101,   4, 116, 208, 458, 266, 183, 198, 169, 487, 295, 218, 340, 298,  66, 123, 348, 447, 433, 383, 379, 268, 214, 456, 439, 311, 139, 230, 498, 484, 478, 262, 453, 251, 229, 207, 108, 83, 403, 470, 443, 271,  88,  32, 367, 162, 469, 308, 407,  51, 485, 377, 489, 496, 113, 345, 448, 504, 135, 323, 368, 149, 131, 488, 155, 385, 511, 365, 156, 166, 176, 260, 473, 339,   5, 283, 280,  61,  95,  28, 349,  72, 509, 446, 315, 191,  37,  34,  21, 197, 415, 364, 476, 341, 358, 147, 153, 125, 170, 181, 194, 436, 394, 390,  54,  81, 237,  15, 160, 269,  62, 386, 209, 275, 273, 64, 499, 120, 457,  75, 330, 384, 317, 501, 281, 254, 145, 444, 203, 303, 475, 133, 347, 472, 223, 143, 137, 395,  18,  29, 236, 459,  87, 329, 129, 508, 332, 380, 161,  19,  96,  24,  80,  23, 91,  69, 263, 369, 371,  77, 228, 250,  46,  70,  67,  10, 327, 463, 127,  11,  42, 119, 334, 406,  35,  45, 235,  41, 174, 274, 238, 344, 316, 414, 265, 404, 418, 486, 115, 114, 355, 505, 304, 357, 256, 221, 219, 450, 267, 150, 408, 292,  26, 297, 168, 118, 319, 177, 337,   8, 204, 405, 309, 225,  12, 479, 397, 278,   9, 276,  31, 410, 461, 399, 434, 321, 477, 503, 370,  99,  89, 188, 78, 438, 353,  71, 167, 320, 172, 398, 360, 382, 291, 245, 378, 246, 138,  17,  74, 124, 252,   0, 422, 244, 157,  50,  14, 350, 393, 306, 122, 190, 288, 402, 142, 222,  16,  92, 206, 313, 411, 216, 342, 261, 400, 389,  84, 117, 502, 483, 189, 290, 431,  43, 201, 227, 210, 430, 148,  68, 241, 363, 493, 182, 366,  57, 435, 465, 212, 199,  60, 146,  22, 226, 421, 507, 376,  53, 354, 130, 324, 184, 318,  49,  93, 333,  39, 258, 247, 440, 413,  59, 424, 165, 270, 429, 445, 464, 480, 401,  38, 442, 322, 289, 164, 231, 97, 328, 500, 175, 375, 301, 255, 286, 305,  44, 215, 428, 343, 52, 151, 449, 506, 388, 136, 248,  98, 132, 134, 234, 326, 374, 158, 243, 249,  48, 173, 200, 452, 482,  79, 140, 104, 312, 272, 359, 437, 373,  13, 381,  55, 196, 351, 106, 296,  40, 300, 392, 186,   3, 495, 126, 325, 154, 462, 362, 259, 481, 491, 441, 467, 335, 372, 109, 494,   1, 285,  25, 314,  36, 185, 178, 426, 492, 107, 187, 195, 277,  85]

        self.grid_order_10 = [591, 415, 411, 905, 539, 368, 714, 506, 488, 228, 856, 482, 858, 407, 403, 323, 829, 626, 371, 77, 232, 653, 891, 92, 370, 813, 175, 427, 408, 915, 995, 521, 789, 433, 67, 528, 325, 588, 544, 516, 652, 160, 782, 589, 899, 412, 621, 203, 584, 581, 938, 737, 888, 47, 234, 393, 658, 820, 93, 372, 781, 775, 937, 139, 580, 85, 985, 803, 960, 980, 237, 784, 733, 917, 128, 462, 447, 876, 461, 753, 641, 341, 843, 907, 110, 105, 600, 265, 23, 156, 363, 367, 841, 297, 874, 419, 951, 41, 762, 165, 682, 527, 704, 627, 613, 149, 622, 252, 609, 898, 113, 394, 817, 281, 900, 366, 178, 881, 213, 642, 46, 740, 647, 216, 935, 29, 698, 22, 352, 19, 127, 962, 478, 610, 759, 707, 319, 457, 383, 897, 357, 805, 748, 134, 320, 918, 345, 109, 410, 715, 335, 353, 4, 513, 45, 657, 585, 853, 114, 824, 177, 822, 132, 422, 689, 438, 131, 844, 167, 181, 391, 697, 973, 454, 258, 361, 570, 97, 768, 28, 864, 212, 37, 179, 596, 162, 280, 878, 170, 184, 708, 2, 651, 683, 640, 979, 307, 52, 747, 517, 862, 205, 618, 529, 840, 531, 913, 202, 764, 518, 147, 78, 699, 469, 423, 857, 34, 709, 552, 927, 389, 358, 992, 562, 649, 1, 563, 453, 887, 314, 800, 43, 629, 68, 837, 637, 574, 866, 72, 250, 390, 794, 569, 150, 896, 920, 299, 117, 44, 432, 716, 176, 26, 282, 532, 399, 788, 164, 692, 9, 676, 186, 694, 695, 833, 210, 48, 15, 861, 129, 838, 91, 263, 991, 661, 934, 835, 233, 424, 998, 555, 473, 157, 943, 309, 182, 603, 452, 311, 910, 810, 266, 169, 444, 241, 327, 956, 188, 257, 807, 140, 542, 359, 686, 20, 793, 769, 804, 523, 215, 583, 787, 174, 942, 656, 73, 294, 706, 582, 111, 577, 460, 606, 463, 121, 329, 116, 253, 35, 751, 732, 392, 154, 537, 719, 287, 931, 564, 339, 290, 828, 534, 474, 437, 662, 540, 826, 251, 957, 193, 235, 440, 104, 288, 435, 55, 272, 961, 166, 796, 249, 912, 405, 152, 53, 725, 701, 381, 612, 530, 119, 211, 993, 590, 648, 285, 718, 655, 260, 214, 514, 936, 439, 286, 509, 133, 221, 308, 275, 559, 362, 443, 825, 550, 868, 666, 254, 291, 994, 779, 680, 413, 705, 143, 62, 839, 21, 515, 3, 155, 735, 384, 70, 755, 968, 332, 123, 120, 986, 373, 922, 355, 561, 284, 501, 632, 338, 304, 445, 883, 467, 790, 665, 982, 579, 799, 63, 360, 734, 639, 758, 450, 490, 118, 197, 939, 832, 500, 894, 449, 988, 711, 587, 244, 378, 103, 909, 557, 667, 659, 965, 135, 465, 192, 558, 535, 889, 38, 448, 400, 746, 811, 446, 953, 673, 66, 356, 279, 996, 455, 895, 125, 631, 739, 239, 599, 821, 397, 636, 766, 18, 736, 82, 549, 99, 401, 61, 690, 436, 638, 989, 108, 16, 713, 472, 245, 507, 687, 972, 185, 240, 566, 710, 141, 785, 90, 209, 451, 495, 404, 903, 315, 42, 981, 79, 347, 729, 330, 479, 39, 480, 302, 295, 884, 669, 545, 893, 761, 717, 242, 486, 49, 846, 382, 946, 144, 264, 977, 771, 767, 406, 777, 831, 269, 5, 904, 434, 57, 496, 869, 497, 693, 208, 932, 56, 101, 928, 873, 122, 100, 354, 560, 145, 337, 475, 595, 721, 8, 420, 538, 818, 575, 752, 191, 852, 255, 678, 880, 187, 670, 301, 567, 236, 380, 774, 634, 770, 547, 270, 396, 303, 124, 83, 646, 802, 624, 74, 130, 966, 819, 750, 218, 336, 441, 508, 671, 385, 617, 724, 426, 568, 0, 503, 978, 823, 773, 340, 51, 684, 225, 967, 344, 136, 541, 7, 376, 668, 493, 386, 402, 96, 262, 276, 84, 741, 76, 33, 318, 231, 801, 431, 224, 797, 834, 172, 700, 875, 949, 619, 351, 305, 24, 278, 342, 916, 200, 941, 194, 468, 554, 879, 754, 757, 466, 812, 425, 576, 923, 925, 98, 416, 10, 911, 688, 827, 95, 908, 565, 40, 744, 969, 106, 954, 553, 702, 664, 151, 102, 201, 863, 81, 792, 615, 749, 87, 248, 886, 115, 964, 388, 50, 267, 890, 316, 892, 206, 958, 350, 578, 227, 476, 13, 247, 872, 107, 608, 25, 926, 456, 974,  6, 30, 870, 94, 499, 760, 919, 983, 12, 720, 198, 246, 65, 644, 489, 959, 271, 594, 546, 786, 798, 510, 333, 519, 171, 663, 86, 328, 229, 851, 89, 847, 17, 283, 743, 620, 421, 395, 60, 322, 442, 313, 484, 616, 409, 614, 975, 158, 369, 997, 293, 226, 756, 195, 58, 32, 296, 524, 536, 703, 940, 630, 650, 836, 153, 806, 999, 551, 428, 348, 783, 54, 633, 458, 161, 660, 877, 491, 944, 321, 865, 947, 906, 173, 256, 830, 742, 765, 848, 685, 791, 712, 990, 871, 728, 429, 625, 414, 492, 924, 326, 730, 238, 223, 142, 138, 289, 597, 349, 64, 901, 814, 572, 525, 220, 526, 727, 675, 207, 745, 11, 180, 723, 204, 921, 645, 27, 365, 882, 398, 722, 643, 573, 159, 36, 306, 259, 628, 31, 504, 855, 533, 607, 485, 520, 459, 334, 292, 933, 976, 623, 815, 312, 331, 854, 190, 88, 375, 778, 14, 487, 317, 592, 930, 952, 963, 859, 418, 168, 343, 885, 955, 71, 548, 571, 948, 346, 377, 763, 502, 795, 498, 481, 691, 842, 945, 902, 816, 277, 146, 196, 189, 681, 374, 126, 845, 364, 217, 324, 222, 971, 867, 298, 183, 635, 430, 59, 512, 984, 471, 987, 808, 850, 75, 556, 199, 593, 274, 605, 80, 849, 950, 914, 929, 477, 112, 300, 602, 230, 163, 522, 780, 674, 69, 268, 726, 679, 860, 586, 494, 672, 604, 505, 776, 611, 970, 511, 738, 731, 417, 483, 273, 601, 772, 387, 543, 696, 470, 464, 809, 310, 261, 654, 598, 677, 137, 148, 243, 379, 219]

        self.initialize_nonlinear_grid()

        # transform we optimize over is the source landmarks (initialize to identity, equal to target landmarks)
        self.initial_transform = self.target_landmarks

        # internal recordkeeping
        self.iterations = 0

        # keep track of the best objective we have seen so far to return that when computation stops.
        self.minimum_objective = numpy.inf

    def initialize_nonlinear_grid(self):
        self.target_landmarks = list()
        if self.nonlinear_grid_resolution == 3:
            grid = self.nonlinear_grid_3
            grid_order = self.grid_order_3
        elif self.nonlinear_grid_resolution == 4:
            grid = self.nonlinear_grid_4
            grid_order = self.grid_order_4
        elif self.nonlinear_grid_resolution == 5:
            grid = self.nonlinear_grid_5
            grid_order = self.grid_order_5                        
        elif self.nonlinear_grid_resolution == 6:
            grid = self.nonlinear_grid_6
            grid_order = self.grid_order_6
        elif self.nonlinear_grid_resolution == 8:
            grid = self.nonlinear_grid_8
            grid_order = self.grid_order_8
        elif self.nonlinear_grid_resolution == 10:
            grid = self.nonlinear_grid_10
            grid_order = self.grid_order_10
        else:
            print "<congeal_multisubject.py> Error: Unknown nonlinear grid mode:", self.nonlinear_grid_resolution
        tmp = list()
        for r in grid:
            for a in grid:
                for s in grid:
                    tmp.append([r, a, s])
        # now shuffle the order of these points to avoid biases
        for idx in grid_order:
            self.target_landmarks.extend(tmp[idx])
        self.target_points = convert_numpy_array_to_vtk_points(self.target_landmarks)
        
    def objective_function(self, current_x):
        """ The actual objective used in registration.  Function of
        the current x in search space, as well as parameters of the
        class: threshold, sigma. Compares sampled fibers from moving
        input, to all fibers of fixed input."""

        # get and apply transforms from current_x
        moving = self.transform_fiber_array_numpy(self.moving, current_x)

        # compute objective
        obj = inner_loop_objective(self.fixed, moving, self.sigma * self.sigma)

        # TEST
        #obj2 = wma.register_two_subjects.inner_loop_objective(self.fixed, moving, self.sigma * self.sigma)
        #print "OBJECTIVE TEST:", obj, obj2, obj - obj2

        # keep track of minimum objective so far and its matching transform
        if obj < self.minimum_objective:
            #print "OBJECTIVE:", obj, "PREV MIN",  self.minimum_objective
            self.minimum_objective = obj
            # must copy current_x into allocated memory space to keep the value
            self.final_transform[:] = current_x

        # save objective function value for analysis of performance
        self.objective_function_values.append(obj)

        if self.verbose:
            print "O:",  obj, "X:", current_x
        #print "X:", self._x_opt
        return obj

    def transform_fiber_array_numpy(self, in_array, source_landmarks):
        """Transform in_array of R,A,S by transform (a list of source points).  Transformed fibers are returned.
        """
        (dims, number_of_fibers, points_per_fiber) = in_array.shape
        out_array = numpy.zeros(in_array.shape)

        vtktrans = convert_transform_to_vtk(source_landmarks, self.target_points)
        #print "2:", vtktrans
        #vtktrans = vtk.vtkTransform()
        
        # Transform moving fiber array by applying transform to original fibers
        for lidx in range(0, number_of_fibers):
            for pidx in range(0, points_per_fiber):
                pt = vtktrans.TransformPoint(in_array[0, lidx, pidx],
                                            in_array[1, lidx, pidx], 
                                            in_array[2, lidx, pidx])
                out_array[0, lidx, pidx] = pt[0]
                out_array[1, lidx, pidx] = pt[1]
                out_array[2, lidx, pidx] = pt[2]

        #print in_array[0, lidx, pidx], in_array[1, lidx, pidx], in_array[2, lidx, pidx], "===>>>", out_array[0, lidx, pidx], out_array[1, lidx, pidx], out_array[2, lidx, pidx]
        del vtktrans

        ## uncomment for testing only
        ## # convert it back to a fiber object and render it
        ## global __render_count
        ## if (numpy.mod(__render_count, 500) == 0) & False:
        ##     fiber_array = wma.fibers.FiberArray()
        ##     fiber_array.fiber_array_r = out_array[0,:,:]
        ##     fiber_array.fiber_array_a = out_array[1,:,:]
        ##     fiber_array.fiber_array_s = out_array[2,:,:]
        ##     fiber_array.points_per_fiber = points_per_fiber
        ##     fiber_array.number_of_fibers = number_of_fibers
        ##     pd = fiber_array.convert_to_polydata()
        ##     ren = wma.render.render(pd, number_of_fibers, verbose=False)
        ##     ren.save_views('.', 'moving_{0:05d}_'.format(__render_count)+str(time.clock())[-5:-1])
        ##     del ren
        ## __render_count += 1

        return out_array

    def compute(self):

        """ Run the registration.  Add subjects first (before calling
        compute). Then call compute several times, using different
        parameters for the class, for example first just for
        translation."""

        # subject data must be input first. No check here for speed
        #self.fixed = None
        #self.moving = None
        #self.initial_transform = None

        # This is left if needed in future for debugging.
        # convert it back to a fiber object and render it
        ## (dims, number_of_fibers_moving, points_per_fiber) = self.moving.shape
        ## fiber_array = wma.fibers.FiberArray()
        ## fiber_array.fiber_array_r = self.moving[0,:,:]
        ## fiber_array.fiber_array_a = self.moving[1,:,:]
        ## fiber_array.fiber_array_s = self.moving[2,:,:]
        ## fiber_array.points_per_fiber = points_per_fiber
        ## fiber_array.number_of_fibers = number_of_fibers_moving
        ## pd = fiber_array.convert_to_polydata()
        ## ren = wma.render.render(pd, number_of_fibers_moving, verbose=False)
        ## ren.save_views('.', 'moving_brain_{0:05d}_'.format(self.iterations)+str(time.clock())[-5:-1])
        ## #ren.save_views('.', 'moving_brain_{0:05d}'.format(self.iterations))
        ## del ren

        # For debugging/monitoring of progress
        if self.render:
            (dims, number_of_fibers_fixed, points_per_fiber) = self.fixed.shape
            fiber_array = wma.fibers.FiberArray()
            fiber_array.fiber_array_r = self.fixed[0,:,:]
            fiber_array.fiber_array_a = self.fixed[1,:,:]
            fiber_array.fiber_array_s = self.fixed[2,:,:]
            fiber_array.points_per_fiber = points_per_fiber
            fiber_array.number_of_fibers = number_of_fibers_fixed
            pd2 = fiber_array.convert_to_polydata()
            ren = wma.render.render(pd2, number_of_fibers_fixed, verbose=False)
            # save low-res images for speed
            ren.magnification = 3
            ren.save_views(self.output_directory, 'fixed_brain_' + self.process_id_string)
            del ren
                
        self.iterations += 1
        self.final_transform = numpy.zeros(self.initial_transform.shape)

        if self.verbose:
            print "<congeal.py> Initial value for X:", self.initial_transform

        # These optimizers were tested, less successfully than cobyla.
        # This code is left here as documentation.
        #scipy.optimize.fmin(self.objective_function,
        #                    self._x_opt, params, maxiter=self.maxiter,
        #                    ftol=self.ftol, maxfun=self.maxfun)
        #self.final_transform = scipy.optimize.fmin_powell(self.objective_function,
        #                                            numpy.multiply(self.initial_transform,self.transform_scaling),
        #                                            xtol=self.rhobeg,
        #                                            ftol = 0.05,
        #                                            maxfun=self.maxfun)
        #maxiter=5)

        # Optimize using cobyla. Allows definition of initial and
        # final step size scales (rhos), as well as constraints.  Here
        # we use the constraints to encourage that the transform stays a transform.
        # note disp 0 turns off all display
        not_used = scipy.optimize.fmin_cobyla(self.objective_function,
                                                  self.initial_transform, self.constraint,
                                                  maxfun=self.maxfun, rhobeg=self.initial_step,
                                                  rhoend=self.final_step, disp=0)

        if self.verbose:
            print "O:", self.objective_function_values

        # Return output transforms from this iteration
        return self.final_transform


def inner_loop_objective(fixed, moving, sigmasq):
    """ The code called within the objective_function to find the
    negative log probability of one brain given all other brains. Used
    with Entropy objective function."""

    (dims, number_of_fibers_moving, points_per_fiber) = moving.shape
    # number of compared fibers (normalization factor)
    (dims, number_of_fibers_fixed, points_per_fiber) = fixed.shape

    probability = numpy.zeros(number_of_fibers_moving) + 1e-20
    
    # Loop over fibers in moving, find total probability of
    # fiber using all fibers from fixed.
    for idx in range(number_of_fibers_moving):
        probability[idx] += total_probability_numpy(moving[:,idx,:], fixed,
                sigmasq)

    # divide total probability by number of fibers in the atlas ("mean
    # brain").  this neglects Z, the normalization constant for the
    # pdf, which would not affect the optimization.
    probability /= number_of_fibers_fixed
    #print "PROBABILITY:", numpy.min(probability), numpy.max(probability),
    # add negative log probabilities of all fibers in this brain.
    entropy = numpy.sum(- numpy.log(probability))
    return entropy

def total_probability_numpy(moving_fiber, fixed_fibers, sigmasq):
    """Compute total probability for moving fiber when compared to all fixed

    fibers.
    """
    distance = fiber_distance_numpy(moving_fiber, fixed_fibers)
    probability = numpy.exp(numpy.divide(-distance, sigmasq))
    ## #print "SIGMAS:", numpy.sqrt(sigmasq), "DIFFS:", numpy.min(diffs), numpy.max(diffs), "PROBABILITY :", numpy.min(probability), numpy.max(probability), probability.shape, "PROBABILITY:", numpy.min(probability), numpy.max(probability), probability.shape, "FIBERS:", moving_fiber.shape, fixed_fibers.shape
    return numpy.sum(probability)

def fiber_distance_numpy(moving_fiber, fixed_fibers):
    """
    Find pairwise fiber distance from fiber to all fibers in fiber_array.
    The Mean and MeanSquared distances are the average distance per
    fiber point, to remove scaling effects (dependence on number of
    points chosen for fiber parameterization). The Hausdorff distance
    is the maximum distance between corresponding points.
    input fiber should be class Fiber. fibers should be class FiberArray
    """
    # compute pairwise fiber distances along fibers
    distance_1 = _fiber_distance_internal_use_numpy(moving_fiber, fixed_fibers)
    distance_2 = _fiber_distance_internal_use_numpy(moving_fiber, fixed_fibers,reverse_fiber_order=True)
    
    # choose the lowest distance, corresponding to the optimal fiber
    # representation (either forward or reverse order)
    return numpy.minimum(distance_1, distance_2)

def _fiber_distance_internal_use_numpy(moving_fiber, fixed_fibers, reverse_fiber_order=False):
    """ Compute the total fiber distance from one fiber to an array of
    many fibers.
    This function does not handle equivalent fiber representations,
    for that use fiber_distance, above.
    """
    #print "SHAPE:", fixed_fibers[0,:,:].shape, moving_fiber[0,::-1].shape
    
    # compute the distance from this fiber to the array of other fibers
    if reverse_fiber_order:
        ddx = fixed_fibers[0,:,:] - moving_fiber[0,::-1]
        ddy = fixed_fibers[1,:,:] - moving_fiber[1,::-1]
        ddz = fixed_fibers[2,:,:] - moving_fiber[2,::-1]
    else:
        ddx = fixed_fibers[0,:,:] - moving_fiber[0,:]
        ddy = fixed_fibers[1,:,:] - moving_fiber[1,:]
        ddz = fixed_fibers[2,:,:] - moving_fiber[2,:]

    #print "MAX abs ddx:", numpy.max(numpy.abs(ddx)), "MAX ddy:", numpy.max(numpy.abs(ddy)), "MAX ddz:", numpy.max(numpy.abs(ddz))
    #print "MIN abs ddx:", numpy.min(numpy.abs(ddx)), "MIN ddy:", numpy.min(numpy.abs(ddy)), "MIN ddz:", numpy.min(numpy.abs(ddz))
    
    dx = numpy.square(ddx)
    dy = numpy.square(ddy)
    dz = numpy.square(ddz)

    distance = dx + dy + dz

    # Use the mean distance as it works better than Hausdorff-like distance
    return numpy.mean(distance, 1)

    # Hausdorff
    # take max along fiber
    #return numpy.max(distance, 1)

def convert_numpy_array_to_vtk_points(inarray):
    """ Convert numpy array or flat list of points to vtkPoints."""
    
    number_of_points = len(inarray)/3
    vtk_points = vtk.vtkPoints()
    vtk_points.SetNumberOfPoints(number_of_points)
    idx = 0
    for pt in zip(inarray[::3], inarray[1::3], inarray[2::3]):
        #print pt
        vtk_points.SetPoint(idx, pt[0], pt[1], pt[2])
        idx += 1
    return vtk_points

def convert_transform_to_vtk(source_landmarks, target_points):
    """Produce an output vtkThinPlateSplineTransform corresponding to the

    registration results. Input is a numpy array of of source (moving)
    landmarks and a vtkPoints object of target (fixed) landmarks.
    """

    source_points = convert_numpy_array_to_vtk_points(source_landmarks)
    #number_of_points = len(source_landmarks)/3
    #print "CONVERT:", len(source_landmarks), number_of_points, target_points.GetNumberOfPoints(), source_points.GetNumberOfPoints()

    return compute_thin_plate_spline_transform(source_points, target_points)

def compute_thin_plate_spline_transform(source_points, target_points):
    """Produce an output vtkThinPlateSplineTransform.
    Input is a vtkPoints object of source (moving) landmarks and a vtkPoints
    object of target (fixed) landmarks.
    """
    vtktrans = vtk.vtkThinPlateSplineTransform()
    vtktrans.SetSourceLandmarks(source_points)
    vtktrans.SetTargetLandmarks(target_points)
    vtktrans.SetBasisToR()
    
    return vtktrans

