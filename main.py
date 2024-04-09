# For 242P - Compilers
# Author: Brandon Wang
#
# 

import argparse
from smpl_parser import Parser
from visualizer import Visualizer

def main():
    # Parse command line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument('file', type=str)
    args = argparser.parse_args()

    # Pass file into the parser
    parser = Parser(args.file)
    blocks = parser.Parse()
    viz = Visualizer(blocks)
    viz.Construct()
    print(viz.Output())


if __name__ == '__main__':
    main()