import unittest

import mock
import numpy

import cupy
try:
    import cupy.cuda.cudnn as libcudnn
    cudnn_enabled = True
    modes = [
        libcudnn.CUDNN_ACTIVATION_SIGMOID,
        libcudnn.CUDNN_ACTIVATION_RELU,
        libcudnn.CUDNN_ACTIVATION_TANH,
    ]
    import cupy.cudnn
except ImportError:
    cudnn_enabled = False
    modes = []
from cupy import testing


@testing.parameterize(*testing.product({
    'dtype': [numpy.float32, numpy.float64],
    'mode': modes,
}))
@unittest.skipUnless(
    cudnn_enabled and libcudnn.getVersion() >= 3000,
    'cuDNN >= 3.0 is supported')
class TestCudnnActivation(unittest.TestCase):

    def setUp(self):
        self.x = testing.shaped_arange((3, 4), cupy, self.dtype)
        self.y = testing.shaped_arange((3, 4), cupy, self.dtype)
        self.g = testing.shaped_arange((3, 4), cupy, self.dtype)

    def test_activation_forward_version(self):
        if libcudnn.getVersion() >= 4000:
            patch = 'cupy.cuda.cudnn.activationForward_v4'
        else:
            patch = 'cupy.cuda.cudnn.activationForward_v3'
        with mock.patch(patch) as func:
            cupy.cudnn.activation_forward(self.x, self.mode)
            self.assertEqual(func.called, True)

    def test_activation_backward_version(self):
        if libcudnn.getVersion() >= 4000:
            patch = 'cupy.cuda.cudnn.activationBackward_v4'
        else:
            patch = 'cupy.cuda.cudnn.activationBackward_v3'
        with mock.patch(patch) as func:
            cupy.cudnn.activation_backward(self.x, self.y, self.g, self.mode)
            self.assertEqual(func.called, True)


@testing.parameterize(*testing.product({
    'dtype': [numpy.float32, numpy.float64],
    'ratio': [0.0, 0.1, 0.2, 0.5],
    'seed': [0, 100]
}))
@unittest.skipUnless(
    cudnn_enabled and libcudnn.getVersion() >= 5000,
    'cuDNN >= 5.0 is supported')
class TestCudnnDropout(unittest.TestCase):

    def setUp(self):
        self.x = testing.shaped_arange((3, 4), cupy, self.dtype)
        self.gy = testing.shaped_arange((3, 4), cupy, self.dtype)
        self.states = cupy.cudnn.DropoutStates(
            cupy.cudnn.get_handle(), self.seed)

    def test_dropout_forward(self):
        _, y = self.states.forward(
            cupy.cudnn.get_handle(), self.x, self.ratio)
        if self.ratio == 0:
            self.assertTrue(cupy.all(self.x == y))
        else:
            self.assertTrue(cupy.all(self.x != y))

    def test_dropout_backward(self):
        rspace, y = self.states.forward(
            cupy.cudnn.get_handle(), self.x, self.ratio)
        gx = self.states.backward(
            cupy.cudnn.get_handle(), self.gy, self.ratio, rspace)

        forward_mask = y / self.x
        backward_mask = gx / self.gy

        # backward_mask must be the same as forward_mask
        self.assertTrue(cupy.all(forward_mask == backward_mask))

    def test_dropout_seed(self):
        handle = cupy.cudnn.get_handle()

        # initialize Dropoutstates with the same seed
        states2 = cupy.cudnn.DropoutStates(handle, self.seed)

        rspace, y = self.states.forward(handle, self.x, self.ratio)
        rspace2, y2 = states2.forward(handle, self.x, self.ratio)
        # forward results must be the same
        self.assertTrue(cupy.all(y == y2))

        gx = self.states.backward(handle, self.gy, self.ratio, rspace)
        gx2 = states2.backward(handle, self.gy, self.ratio, rspace2)
        # backward results must be the same
        self.assertTrue(cupy.all(gx == gx2))
