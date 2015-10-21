import unittest

import numpy

import chainer
from chainer import cuda
from chainer import functions
from chainer import gradient_check
from chainer import testing
from chainer.testing import attr


class TestGetItem(unittest.TestCase):
    in_shape = (10, 5)
    out_shape = (10,)

    def setUp(self):
        self.x_data = numpy.random.uniform(
            -1, 1, self.in_shape).astype(numpy.float32)
        self.t_data = numpy.random.randint(
            0, 2, self.out_shape).astype(numpy.int32)
        self.gy_data = numpy.random.uniform(
            -1, 1, self.out_shape).astype(numpy.float32)

    def check_forward(self, x_data, t_data):
        x = chainer.Variable(x_data)
        t = chainer.Variable(t_data)
        y = functions.getitem(x, t)
        y_exp = cuda.to_cpu(x_data)[range(t_data.size), cuda.to_cpu(t_data)]

        numpy.testing.assert_equal(cuda.to_cpu(y.data), y_exp)

    def test_forward_cpu(self):
        self.check_forward(self.x_data, self.t_data)

    @attr.gpu
    def test_forward_gpu(self):
        self.check_forward(cuda.to_gpu(self.x_data),
                           cuda.to_gpu(self.t_data))

    def check_backward(self, x_data, t_data, gy_data):
        x = chainer.Variable(x_data)
        t = chainer.Variable(t_data)
        y = functions.getitem(x, t)
        y.grad = gy_data
        y.backward()
        self.assertEqual(None, t.grad)

        func = y.creator
        f = lambda: func.forward((x.data, t.data))
        gx, = gradient_check.numerical_grad(f, (x.data,), (gy_data,), eps=0.01)

        gradient_check.assert_allclose(gx, x.grad)

    def test_backward_cpu(self):
        self.check_backward(self.x_data, self.t_data, self.gy_data)

    @attr.gpu
    def test_backward_gpu(self):
        self.check_backward(cuda.to_gpu(self.x_data),
                            cuda.to_gpu(self.t_data),
                            cuda.to_gpu(self.gy_data))


class TestGetItemZeroSize(unittest.TestCase):
    in_shape = (0, 5)
    out_shape = (0,)


testing.run_module(__name__, __file__)
