#ifndef VIDEOEDITOR_IMAGE_H
#define VIDEOEDITOR_IMAGE_H

#include <vector>

/// A image class, containing a rectangular table of pixels.
///
/// ----- Pixels -----
/// Pixel is the basic component of a image, represents a tiny square cell filled by a color.
///
/// Learn more about pixel: https://en.wikipedia.org/wiki/Pixel
///
/// ----- Width and height -----
/// A image is a rectangle. The width and height of this rectangle represent the number of columns and rows of the grid.
/// Its also called resolution, usually quoted as "width × height", e.g. "1920 x 1080".
///
/// ----- Order of pixels -----
/// In our image class, pixels they are stored row by row, from top to bottom
/// then from left to right in each row.
/// So the pixel at i's row, j's column is pixels[i * width + j]
///
/// For example, in a 3x3 image looks like
/// A, B, C
/// D, E, F
/// G, H, I
///
/// then the elements of pixels are [A, B, C, D, E, F, G, H, I]
/// the pixels A is pixels[0*3 + 0], or pixels[0]
/// the pixels H is pixels[2*3 + 1], or pixels[7]
///
/// ----- Pixel and color -----
/// There are many representations of color, for example,
/// - Black and white photo: we only need a non-negative value to represent the brightness,
///   see https://en.wikipedia.org/wiki/Black_and_white,
///   Its type is Image<float>, the range of the float is [0, 1] (0 = black, 1 = white, others are gray of different brightness)
///
/// - A colorful RGB image: a mixture of 3 colors, Red, Green and Blue, with different intensities.
///   See http://www.rapidtables.com/web/color/RGB_Color.htm
///   A common 24-bit RGB color uses three 8-bit non-negative integers in [0, 1, 2 ... 255] (0,0,0 = black, 255,255,255 = white)
///   define as class RGB { int r, g, b  };
///   The the image type is Image<RGB>
///
/// - Pixel made by characters: we use it to draw ASCII art in console, such as:
///   ****************************************************************
///   *   ____    ___    __  __   ____    ____     ___    _   ____   *
///   *  / ___|  / _ \  |  \/  | |  _ \  |___ \   / _ \  | | |___ \  *
///   * | |     | | | | | |\/| | | |_) |   __) | | | | | | |   __) | *
///   * | |___  | |_| | | |  | | |  __/   / __/  | |_| | | |  / __/  *
///   *  \____|  \___/  |_|  |_| |_|     |_____|  \___/  |_| |_____| *
///   *                                                              *
///   ****************************************************************
///   (converted on http://patorjk.com/software/taag)
///   Because in this application, we do not provide a video player, so we can print the pixels on screen.
///   The type is Image<char>
///
/// To support different kind of representation of pixel, we use a template parameter PixelType for abstraction.
template <typename PixelType>
class Image {
public:
    /// Construct a image from pixels in array
    /// Note: it may cause some problem if the size of vector is not width * height
    explicit Image(unsigned long width, unsigned long height, const PixelType pixels[]);

    /// Construct a image from pixels in vector
    /// Note: it may cause some problem if the size of vector is not width * height
    explicit Image(unsigned long width, unsigned long height, const std::vector<PixelType>& pixels);

    /// Construct an image by copying from a given image.
    Image(const Image& image);

    Image& operator=(const Image& image);

    /// return the width of image
    unsigned long getWidth() const;

    /// return the height of image
    unsigned long getHeight() const;

    /// The operator help you access a pixel at position (row, col).
    /// e.g. image(20, 12) return the pixel at 21th row, 13rd column
    const PixelType& operator()(unsigned long row, unsigned long column) const;

    /// Use this operator to modify a pixel at position (row, col).
    /// e.g. image(20, 12) = 0.8 to change the pixel at 21th row, 13rd column to 0.8
    PixelType& operator()(unsigned long row, unsigned long column);

    /// Translate all pixels to the left by a certain distance, and fill the pixel on the right side
    void moveLeft(unsigned long distance, PixelType fillPixel);

    /// Translate all pixels to the right by a certain distance, and fill the pixel on the left side
    void moveRight(unsigned long distance, PixelType fillPixel);

private:

    /// Dimensions of the video, e.g. 1920 x 1080, means 1080 rows and 1920 columns
    unsigned long width, height;

    /// A vector storing the pixels.
    std::vector<PixelType> pixels;
};

// Usually, we put implementations in .cpp files.
// Unfortunately we cannot hide implementations for class templates,
// so we put them in a separate file (usually .tpp files) to make this .h cleaner
// In this assignment, we put them in .h files, so that old IDEs can recognized them.
#include "ImageImpl.h"

#endif //VIDEOEDITOR_IMAGE_H
