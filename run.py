import sys
import minecraft_print

if __name__ == "__main__":

    if len(sys.argv[1:]) == 12:
        m1 = [ int(a) for a in sys.argv[3:8]]
        m2 = [ int(a) for a in sys.argv[8:]]
        mp = minecraft_print.MinecraftPrint(sys.argv[1], sys.argv[2], m1, m2)
        mp.generate()
    else:
        print "Try the following syntax: python run.py levelname outputname  x z dx dz dy x z dx dz dy"
