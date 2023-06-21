import os
import random
from PIL import Image, ImageDraw, ImageFont

def generate_image_with_text(text):
    # Specify the directory. This is where you will place your template photos that you want the bot to use when tweeting. I made 10 for example with a blank space where the text would be placed.
    directory = r'D:\Templates'

    # Get a list of all files in the directory
    files = os.listdir(directory)

    # Randomly select a file
    file = random.choice(files)

    # Load an image
    image = Image.open(os.path.join(directory, file))

    # Initialize ImageDraw
    draw = ImageDraw.Draw(image)

    # Specify the font, size, and color
    font_size = 30
    font = ImageFont.truetype('arial.ttf', font_size)
    text_color = (0, 0, 0)  # RGB color

    # Define the width and height of the area where you want to place the text
    area_width = 512
    area_height = 512

    # The function below was used to format my text properly such that it looks asthetically pleasing on the photo.
    def wrap_text(text, font, max_width):
        lines = []

        # Split the line by spaces to get words
        words = text.split(' ')
        i = 0

        # Append every word to a line while its width is shorter than the image width
        while i < len(words):
            line = ''
            while i < len(words) and font.getlength(line + words[i]) <= max_width:
                line = line + words[i] + " "
                i += 1

            # If the line is still empty, it means the word is too long to fit in the area width
            # In this case, split the word
            if not line:
                word = words[i]
                for j in range(len(word)):
                    if font.getlength(word[:j+1]) > max_width:
                        line = word[:j]
                        words[i] = word[j:]
                        break
                else:
                    line = words[i]
                    i += 1

            # Add the line to the line list
            lines.append(line)
        return lines

    # Wrap the text
    wrapped_text = wrap_text(text, font, area_width)

    # Join the lines into a single string with line breaks
    wrapped_text = '\n'.join(wrapped_text)

    # Add the signature. This adds a signature to your photo.
    wrapped_text += '\n\n@Insert Your Twitter Handle'

    # Calculate the width and height of the text
    text_width, text_height = draw.multiline_textbbox((0, 0), wrapped_text, font=font)[2:]

    # Calculate the position where you should start drawing the text so that it's centered
    center_x, center_y = 1040, 322
    position = (center_x - area_width / 2, center_y - text_height / 2)

    # Add the text to the image
    draw.multiline_text(position, wrapped_text, font=font, fill=text_color, align='left')

    try:
        # Save the image. Specify where you want the image to be saved. I have this setup to overwrite the image each time as I do not need to keep every image.
        output_path = r'D:\Templates\Outputs\new.png'
        image.save(output_path)
    except Exception as e:
        print(f"An error occurred while saving the image: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Output path: {output_path}")
        print(f"Is directory writable: {os.access(os.path.dirname(output_path), os.W_OK)}")
        raise

    return output_path
