import unittest

def suite():
    """
    Discovers all tests in the current directory and returns a test suite.
    """
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('.', pattern='test_*.py')
    return test_suite

if __name__ == '__main__':
    # Set verbosity to 2 for detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = suite()
    runner.run(test_suite)