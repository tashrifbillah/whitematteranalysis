""" register.py

implementation of fiber tractography registration (group)

class RegisterTractographyNonrigid


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
import vtk.util.numpy_support

try:
    from joblib import Parallel, delayed
    USE_PARALLEL = 1
except ImportError:
    USE_PARALLEL = 0
    print "<congeal.py> Failed to import joblib, cannot multiprocess."
    print "<congeal.py> Please install joblib for this functionality."

import whitematteranalysis as wma

class RegisterTractographyNonrigid(wma.register_two_subjects.RegisterTractography):

    def constraint(self, x_current):
        # Make sure the optimizer is searching in a reasonable region.
        # TEST: Don't let the translations grow too large
        penalty = 10.0 - numpy.mean(numpy.abs(x_current))

        # progress report sometimes
        
        iters = len(self.objective_function_values)
        print_every = int(self.maxfun  / 10)
        if iters % print_every == 0:
            print iters, "/", self.maxfun
            
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

        # set up default grid
        #self.nonrigid_grid_resolution = 3
        #self.nonrigid_grid_resolution = 5
        self.nonrigid_grid_resolution = 6
        self.initialize_nonrigid_grid()

        # transform we optimize over
        self.initial_transform = self.displacement_field_numpy

        # internal recordkeeping
        self.iterations = 0

        # keep track of the best objective we have seen so far to return that when computation stops.
        self.minimum_objective = numpy.inf

        # choice of optimization method
        #self.optimizer = "Powell"
        self.optimizer = "Cobyla"
        #self.optimizer = "BFGS"
        print "OPTIMIZER:", self.optimizer

    def initialize_nonrigid_grid(self):
        res = self.nonrigid_grid_resolution
        self.displacement_field_numpy = numpy.zeros(res*res*res*3)
        #self.displacement_field_vtk = numpy_support.numpy_to_vtk(num_array=NumPy_data.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        
    def objective_function(self, current_x):
        """ The actual objective used in registration.  Function of
        the current x in search space, as well as parameters of the
        class: threshold, sigma. Compares sampled fibers from moving
        input, to all fibers of fixed input."""

        # get and apply transforms from current_x
        moving = self.transform_fiber_array_numpy(self.moving, current_x)

        # compute objective
        obj = wma.register_two_subjects.inner_loop_objective(self.fixed, moving, self.sigma * self.sigma)

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

    def transform_fiber_array_numpy(self, in_array, transform):
        """Transform in_array of R,A,S by transform (a list of source points).  Transformed fibers are returned.
        """
        (dims, number_of_fibers, points_per_fiber) = in_array.shape
        out_array = numpy.zeros(in_array.shape)

        vtktrans = convert_transform_to_vtk(transform)
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

        if self.optimizer == "Cobyla":

            # Optimize using cobyla. Allows definition of initial and
            # final step size scales (rhos), as well as constraints.  Here
            # we use the constraints to encourage that the transform stays a transform.
            # note disp 0 turns off all display
            self.final_transform = scipy.optimize.fmin_cobyla(self.objective_function,
                                                      self.initial_transform, self.constraint,
                                                      maxfun=self.maxfun, rhobeg=self.initial_step,
                                                      rhoend=self.final_step, disp=0)
        elif self.optimizer == "BFGS":
            # Test optimization with BFGS
            # (Broyden-Fletcher-Goldfarb-Shanno algorithm) refines at each
            # step an approximation of the Hessian.  L-BFGS:
            # Limited-memory BFGS Sits between BFGS and conjugate
            # gradient: in very high dimensions (> 250) the Hessian matrix
            # is too costly to compute and invert. L-BFGS keeps a low-rank
            # version. In addition, the scipy version,
            # scipy.optimize.fmin_l_bfgs_b(), includes box bounds.
            # Note If you do not specify the gradient to the L-BFGS
            # solver, you need to add approx_grad=1
            # list of (min,max) pairs for the values being optimized. Assume we never should move by >30mm
            bounds = list()
            for lm in self.target_landmarks:
                bounds.append((lm-30,lm+30))
            ## (self.final_transform, f, dict) = scipy.optimize.fmin_l_bfgs_b(self.objective_function,
            ##                                                                self.initial_transform,
            ##                                                                approx_grad = True,
            ##                                                                maxfun=self.maxfun,
            ##                                                                maxiter=self.maxfun,
            ##                                                                factr=1e12,
            ##                                                                epsilon=self.final_step,
            ##                                                                iprint=0,
            ##                                                                bounds=bounds)
            (self.final_transform, f, dict) = scipy.optimize.fmin_l_bfgs_b(self.objective_function,
                                                                           self.initial_transform,
                                                                           approx_grad = True,
                                                                           maxiter=self.maxfun,
                                                                           factr=1e12,
                                                                           epsilon=self.final_step,
                                                                           iprint=0)
            print f, dict

        elif self.optimizer == "Powell":
            # Test optimization with Powell's method
            # Powell’s method is a conjugate direction method.
            #(self.final_transform, fopt, direc, iters, funcalls, warnflag, allvecs)
            (self.final_transform, fopt, direc, iters, funcalls, warnflag) = scipy.optimize.fmin_powell(self.objective_function,
                                                                            self.initial_transform,
                                                                            xtol=self.initial_step,
                                                                            ftol=self.final_step,
                                                                            maxfun=self.maxfun,
                                                                            maxiter=self.maxfun,
                                                                            disp=1, full_output=True)

            print "TRANS:", self.final_transform, "FLAG:", warnflag

        else:
            print "Unknown optimizer."

        if self.verbose:
            print "O:", self.objective_function_values

        # Return output transforms from this iteration
        return self.final_transform

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

def convert_transform_to_vtk(transform):
    """Produce an output vtkBSplineTransform corresponding to the

    registration results. Input is a numpy array corresponding to the displacement field.
    """
    displacement_field_vtk = vtk.util.numpy_support.numpy_to_vtk(num_array=transform, deep=True, array_type=vtk.VTK_FLOAT)
    displacement_field_vtk.SetNumberOfComponents(3)
    displacement_field_vtk.SetName('DisplacementField')
    grid_image = vtk.vtkImageData()
    grid_image.SetScalarTypeToFloat()
    grid_image.GetPointData().SetScalars(displacement_field_vtk)
    grid_image.SetNumberOfScalarComponents(3)

    # this is a hard-coded assumption about where the polydata is located in space.
    # other code should check that it is centered.
    # This code uses a grid of 200mm x 200mm x 200mm
    #spacing origin extent
    num_vectors = len(transform) / 3
    dims = numpy.power(num_vectors, 1.0/3.0)
    size_mm = 200.0
    origin = -size_mm / 2.0
    # assume 200mm x 200mm x 200mm grid
    spacing = size_mm / (dims - 1)
    grid_image.SetOrigin(origin, origin, origin)
    grid_image.SetSpacing(spacing, spacing, spacing)
    grid_image.SetExtent(0, dims-1, 0, dims-1, 0, dims-1)
    #grid_image.SetDimensions(dims, dims, dims)
    #print "CONVERT TXFORM:", num_vectors, dims, grid_image.GetExtent()
    
    #print "GRID:", grid_image
    coeff = vtk.vtkImageBSplineCoefficients()
    coeff.SetInput(grid_image)
    coeff.Update()
    # this was in the test code.
    coeff.UpdateWholeExtent()
    #print "TX:", transform.shape, transform, displacement_field_vtk, grid_image.GetExtent(), coeff.GetOutput().GetExtent()

    vtktrans = vtk.vtkBSplineTransform()
    vtktrans.SetCoefficients(coeff.GetOutput())
    vtktrans.SetBorderModeToZero()

    ## print "~~~~~~~~~~~~~~~~~~~~~~~~"
    ## print "COEFF:",  coeff.GetOutput()
    ## print "*********"
    ## print "COEFF2:", vtktrans.GetCoefficients()
    ## print "======="
    
    return vtktrans


 
