# Tested against gdal version
import os, math, random, shutil, pathlib, sys
from PIL import Image, ImageFilter, ImageEnhance

geotiffinput = r'D:\SomeDir\YourGEOTIFF.tif'
MAPSETNAME = "YourMap"
zoomrange = (0,0) # Zoom ranges up to (0,7). (e.g. (0,0) - (0,3) - (2,4) - etc)
mapID = "76453275" # eight digit number
mapDrawOrder = "24" # 0-31 range
BrightnessCorrection = 0 # Brightness correction
ContrastCorrection = 0 # Contrast correction
ShowTiles = 0 # Debug tiles (Show [number] of sequential tiles and close, opens images on default .jpg app)
keepTempDir = 0 # Keep tempdir after finish

bld_gmap32Path = r'D:\mpcdir\bld_gmap32.exe' # Your copy of bld_gmap32.exe
bld_gmapLicensePath = r'D:\mpcdir\yourlicense.mpl' # Your MPC license file
gmtPath = r'D:\Etrex32\MapEngine\gmt.exe' # Gmaptool executable http://www.gmaptool.eu/en/content/gmaptool

TILERWSIZE = 0.0014 # How much (in degrees) each output IMG tile will cover in level zero. Other levels a multiple of this
                    # Base value will be recalculated to fit total source image X extent respecting
                    # source image pixel size (avoid gaps).
TILESIZE = 128  # Tile size in pixels to send to compiler (expect worse GPS render performance with values greater than 256)

def main():
    usertiff = geotiffinput
    ShowTilesc = ShowTiles
    DIR_FILE = os.path.join(geotiffinput)
    DIR_PATH = os.path.dirname(DIR_FILE)
    try:
        os.mkdir(str(DIR_PATH)+'\\TEMPWORK')
    except Exception:
        pass
    tempdirpath = str(DIR_PATH) + '\\TEMPWORK\\'
    filename = geotiffinput.split(str(DIR_PATH)+'\\')[1].split('.')[0]
    epsg = getEPSG(usertiff)
    if epsg != "4326":
        print("Please wait, reprojecting to WGS84 (EPSG:4326) \n")
        usertiff = tempdirpath + filename + "_EPSG_4326.tif"
        reprojectc = 'gdalwarp -r bilinear -t_srs "EPSG:4326" ' + geotiffinput + ' ' + usertiff
        reproject = os.popen(reprojectc).read()
        print(reproject)

    gdalinfo = os.popen("gdalinfo -stats " + usertiff).read().splitlines()
    for each in gdalinfo:
        line = each.strip().upper()
        if "UPPER LEFT" in line:
            tcoord = line.split('UPPER LEFT  ( ')[1].split(')')[0].strip()
            MAPVCoordsLeft = float(tcoord.split(',')[0].strip())
            MAPVCoordsTop = float(tcoord.split(',')[1].strip())
        if "LOWER RIGHT" in line:
            tcoord = line.split('LOWER RIGHT ( ')[1].split(')')[0]
            MAPVCoordsRight = float(tcoord.split(',')[0].strip())
            MAPVCoordsBottom = float(tcoord.split(',')[1].strip())
        if "SIZE IS " in line:
            tsize = line.split('SIZE IS ')[1].strip()
            TIFFsizeX = tsize.split(',')[0].strip()
        if "PIXEL SIZE" in line:
            PIXEL_SIZE = float(line.split("(")[1].split(",")[0])

    Xextent = MAPVCoordsRight - MAPVCoordsLeft
    Yextent = MAPVCoordsTop - MAPVCoordsBottom
    Vcoords = []
    TileCount = 0
    print("Please wait, extracting tiles) \n")
    for zoomround in range(zoomrange[1] + 1, zoomrange[0], -1):
        nt1 = Xextent/(TILERWSIZE*zoomround)
        nt2 = round(float(TIFFsizeX)/nt1)
        ZTILERWSIZE = float(nt2)*float(PIXEL_SIZE) #Adjust tile extent to conform exact pixel size
        XTNumber = int(Xextent / ZTILERWSIZE)
        YTNumber = int(Yextent / ZTILERWSIZE)
        XCstep = MAPVCoordsLeft
        YCstep = MAPVCoordsTop
        TileCount = TileCount + (XTNumber * YTNumber)
        for eachY in range(0, YTNumber):
            for eachX in range(0, XTNumber):
                tilename = 'tile_Z' + str(zoomround-1) + '_Y' + str(eachY).zfill(7) + '_X' + str(eachX).zfill(7)
                tilepath = tempdirpath + tilename
                command = "gdal_translate -ot Byte -scale 0 255 -projwin " + str(XCstep) + " " + str(YCstep) + " " + str(
                    XCstep + ZTILERWSIZE) + " " + str(YCstep - ZTILERWSIZE) + " " + usertiff + " " + tilepath + ".tif"
                tileproc = os.popen(command).read()
                print(tileproc)
                coords = []
                coords.append("{:.7f}".format(XCstep)) # VCoordsLeft
                coords.append("{:.7f}".format(YCstep - ZTILERWSIZE)) # VCoordsBottom
                coords.append("{:.7f}".format(XCstep + ZTILERWSIZE)) # VCoordsRight
                coords.append("{:.7f}".format(YCstep)) # VCoordsTop
                tilefilename = tilename
                coords.append(tilefilename)
                coords.append(str(zoomround-1)) # Actual Zoom Level
                Vcoords.append(coords)
                im = Image.open(tilepath + ".tif")
                im = im.resize((TILESIZE, TILESIZE), resample=Image.Resampling.BILINEAR)
                im = im.filter(ImageFilter.SHARPEN)
                if BrightnessCorrection != 0:
                    enhb = ImageEnhance.Brightness(im)
                    im = enhb.enhance(BrightnessCorrection)
                if ContrastCorrection != 0:
                    enhc = ImageEnhance.Contrast(im)
                    im = enhc.enhance(ContrastCorrection)
                if ShowTilesc != 0:
                    im.show()
                    ShowTilesc -= 1
                    if ShowTilesc == 0:
                        quit()
                im.save(tilepath + ".jpg", quality=95)
                os.remove(tilepath + ".tif")
                XCstep += ZTILERWSIZE
            XCstep = MAPVCoordsLeft
            YCstep -= ZTILERWSIZE

    os.remove(geotiffinput + ".aux.xml")
    global MTXfile
    MTXfile = []
    MTXfile.append('H1 ' + "{:.7f}".format(MAPVCoordsLeft) + ' ' + "{:.7f}".format(MAPVCoordsRight) + \
              "{:.7f}".format(MAPVCoordsBottom) + "{:.7f}".format(MAPVCoordsTop) + 'P2016000000065280Raster Map'+'\n')
    getZoomLevels()
    MTXfile.append('H32367070  0    0'+'\n')
    MTXfile.append('H32012270  1'+'\n')
    MTXfile.append('H4LA         7 1252ANSIINTL                      Western European'+'\n') ## ----> Encoding
    MTXfile.append('H4TI '+ mapID + '\n')
    MTXfile.append('H4ID' + mapID +'\n')
    MTXfile.append('H4MD' + mapDrawOrder + '\n')
    MTXfile.append('H4MS   36Raster Map'+'\n') ### -------------------------------------------> MAP SERIES
    MTXfile.append('H4MF  2'+'\n') ### -------------------------------------------> MAP FORMAT
    MTXfile.append('H4MG1'+'\n')
    MTXfile.append('H4CP1' + '\n')
    MTXfile.append('H4CS2' + '\n')
    MTXfile.append('H4CRAny Colour You Like' + '\n')
    MTXfile.append('H4LL0' + '\n')
    MTXfile.append('H4MA  255' + '\n')
    MTXfile.append('H4MB1' + '\n')
    MTXfile.append('H4MC  4' + '\n')
    MTXfile.append('H4ML  255' + '\n')
    MTXfile.append('H4MO0' + '\n')
    MTXfile.append('H4MT1' + '\n')
    MTXfile.append('H4NB1' + '\n')
    MTXfile.append('H4NT0' + '\n')
    MTXfile.append('H4PF1' + '\n')
    MTXfile.append('H4PP0' + '\n')
    MTXfile.append('H4HP0' + '\n')
    MTXfile.append('H4PN01' + '\n')
    MTXfile.append('H4SP1' + '\n')
    MTXfile.append('H4TL150' + '\n')
    MTXfile.append('H4WM0' + '\n')
    MTXfile.append('A3  0      0     462350615020122    0    0'+'\n')
    MTXfile.append('C ' + "{:.7f}".format(MAPVCoordsLeft) + "{:.7f}".format(MAPVCoordsBottom) + 'A ' +
                   "{:.7f}".format(MAPVCoordsLeft) + "{:.7f}".format(MAPVCoordsTop) + 'A ' + \
                   "{:.7f}".format(MAPVCoordsRight) + "{:.7f}".format(MAPVCoordsTop) + 'A ' + \
                   "{:.7f}".format(MAPVCoordsRight) + "{:.7f}".format(MAPVCoordsBottom) + 'A'+'\n')

    for each in Vcoords:
        VCoordsLeft = each[0]
        VCoordsBottom = each[1]
        VCoordsRight = each[2]
        VCoordsTop = each[3]
        tilefilename = each[4]
        ZoomNumber = each[5]
        MTXfile.append('X001  ' + '\n')
        tline = 'X09 ' + VCoordsLeft + ' ' + VCoordsBottom + ' ' + VCoordsRight + ' ' + VCoordsTop \
                       + tilefilename
        toofset = 252 - len(tline)
        tline = tline + ' ' * toofset + str(ZoomNumber) + ' ' + str(ZoomNumber) + '  ' + '0  0'+'\n'
        MTXfile.append(tline)
        MTXfile.append('A3  0      0     4      10823670    0    0' + '\n')
        MTXfile.append('C ' + VCoordsLeft + VCoordsBottom + 'A ' + VCoordsLeft + VCoordsTop + 'A ' + \
                       VCoordsRight + VCoordsTop + 'A ' + VCoordsRight + VCoordsBottom + 'A'+'\n')

    hex2 = str(hex(random.randrange(1000000000, 9999999999))).split('0x')[1].upper()
    outputMTX = tempdirpath + hex2 + '.mtx'
    MTXfilearch = open(outputMTX, 'w')
    MTXfilelen = len(MTXfile)
    TileCount = str(TileCount + 1)
    MTXfilelen = str(MTXfilelen + 1)
    MTXfilelenpl = 10 - len(MTXfilelen)
    TileCountpl = 10 - len(TileCount)

    MTXfilearch.write('H00601' + ' ' * MTXfilelenpl + MTXfilelen + ' ' * TileCountpl + TileCount + '         ' +
                      '0         0'+'\n')
    for line in MTXfile:
        MTXfilearch.write(line)
    MTXfilearch.close()
    command = bld_gmap32Path + ' /mpc ' + bld_gmapLicensePath + ' /nep ' + tempdirpath + hex2 \
              + ' /kt ' + tempdirpath
    print(command)
    os.popen(command).read()
    command = gmtPath + ' -j -m ' + '"' + MAPSETNAME + '"' + ' -o ' + str(DIR_PATH) + '\\' + MAPSETNAME + '.img ' + \
              tempdirpath + hex2 + '.RGN ' + tempdirpath + hex2 + '.LBL ' + \
              tempdirpath + hex2 + '.TRE'
    os.popen(command).read()
    if keepTempDir == 0:
        shutil.rmtree(tempdirpath)

def getEPSG(usertiff):
    epsgtree = []
    gdalinfo = os.popen("gdalinfo -stats " + usertiff).read().splitlines()
    for line in gdalinfo:
        if 'ID["EPSG"' in line:
            epsgtree.append(line)
    epsg = epsgtree.pop().split('ID["EPSG",')[1].split(']]')[0]
    return epsg

def getZoomLevels():
    zoomlevels = [
        'H20     24      59724  0 01', # 5m - 200m
        'H21     35     119423  0 01', # 300m
        'H22     49     238822  0 01', # 500m - 800m
        'H23     69     477721  0 01', # 1.2km
        'H24     98     955420  0 01', # 2km - 3km
        'H25    138    1910919  0 01', # 5km
        'H26    195    3821818  0 01', # 8km - 12km
        'H27    277    7643717  0 01' # 20km
        ]
    for zoomround in range(zoomrange[0], zoomrange[1]+1):
        MTXfile.append(zoomlevels[zoomround] + '\n')

if __name__=="__main__":
	main()