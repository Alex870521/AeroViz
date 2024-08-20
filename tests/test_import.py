import unittest


class TestAeroVizImports(unittest.TestCase):
    def test_imports(self):
        try:
            import AeroViz
            from AeroViz import plot
            from AeroViz.dataProcess import DataProcess
            from AeroViz.rawDataReader import RawDataReader
            from AeroViz.tools import DataBase, DataClassifier

            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"ImportError: {str(e)}")


if __name__ == '__main__':
    unittest.main()
