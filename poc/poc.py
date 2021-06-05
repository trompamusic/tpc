import argparse,shutil

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input1', help="Input 1", required=True)
    parser.add_argument('--input2', help="Input 2", required=True)
    parser.add_argument('--input3', help="Input 3", required=True)
    parser.add_argument('--input4', help="Input 4", required=True)
    parser.add_argument('--param1', help="Param 1", required=True)
    parser.add_argument('--param2', help="Param 2", required=True)
    parser.add_argument('--output1', help="Output 1", required=True)
    parser.add_argument('--output2', help="Output 2", required=True)
    parser.add_argument('--output3', help="Output 1", required=True)

    args = parser.parse_args()

    shutil.copyfile(args.input1, args.output1)
    shutil.copyfile(args.input2, args.output2)

    output3_content = "Input3: " + args.input3 + " \nInput 4: " + args.input4 + "\nParam1: " + args.param1 + \
                      "\n Param2: " + args.param2
    fp = open(args.output3, 'w')
    fp.write(output3_content)
    fp.close()
