import os
import sys
import cv2
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

def draw_bounding_boxes(image_path, data):
    # Load the image
    image = cv2.imread(image_path)
    height, width, _ = image.shape

    # Draw all bounding boxes on the image
    for box in data:
        cv2.rectangle(image, box[0], box[1], (0, 255, 0), 6)

    # Convert the image to RGB format for Matplotlib
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Display the image using Matplotlib
    plt.figure(figsize=(10, 6))
    plt.imshow(image_rgb)
    plt.axis('off')
    plt.show()

def getData(lblPath, shapes):
    bounding_boxes = []
    
    height, width = shapes

    # Read the label file
    with open(lblPath, 'r') as f:
        labels = f.readlines()

    # Iterate through each label
    for label in labels:
        # Parse the label components
        label_components = label.strip().split()
        class_id = int(label_components[0])
        x_center = float(label_components[1])
        y_center = float(label_components[2])
        box_width = float(label_components[3])
        box_height = float(label_components[4])

        # Convert normalized values to pixel coordinates
        x_center_pixel = int(x_center * width)
        y_center_pixel = int(y_center * height)
        box_width_pixel = int(box_width * width)
        box_height_pixel = int(box_height * height)

        # Calculate the top-left and bottom-right corners of the bounding box
        top_left_x = int(x_center_pixel - box_width_pixel / 2)
        top_left_y = int(y_center_pixel - box_height_pixel / 2)
        bottom_right_x = int(x_center_pixel + box_width_pixel / 2)
        bottom_right_y = int(y_center_pixel + box_height_pixel / 2)

        bounding_boxes.append([(top_left_x, top_left_y), (bottom_right_x, bottom_right_y)])
    
    return bounding_boxes

def draw_with_pil(imgPath, data):
    img = Image.open(imgPath, "r")
    img = img.rotate(90)
    imgDraw = ImageDraw.Draw(img)

    # Draw each bounding box
    for box in data:
        imgDraw.rectangle(box, outline="green", width=5)
    
    img.show()

def getImgShape(imgPath):
    with Image.open(imgPath, "r") as img:
        width, height = img.width, img.height

    return (width, height)


if __name__=="__main__":
    lblPath = "../OkulerImages/Boya1/labels/0a87f6f2-IMG_20230821_133417.txt"
    imgPath = "../OkulerImages/Boya1/images/0a87f6f2-IMG_20230821_133417.jpg"
    if not os.path.exists(lblPath) or not os.path.exists(imgPath):
        print("File Opening Error")
        sys.exit(0)

    shapes = getImgShape(imgPath)
    coords = getData(lblPath,shapes)
    draw_with_pil(imgPath,coords)
    draw_bounding_boxes(imgPath,coords)