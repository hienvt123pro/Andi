from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from imutils.video import VideoStream
# import argparse
# from collections import Counter
import tensorflow as tf
from recognize_face import facenet, detect_face
import imutils
import pickle
import numpy as np
import cv2
import collections
from recognize_face import Name, Statistics, NumberOfPeople, probabilities


# region Set up metrics
MINSIZE = 20
THRESHOLD = [0.6, 0.7, 0.7]
FACTOR = 0.709
IMAGE_SIZE = 182
INPUT_IMAGE_SIZE = 160
CLASSIFIER_PATH = 'facemodel3.pkl'
FACENET_MODEL_PATH = '20180402-114759.pb'
# endregion

# region Repair for recognition
with open(CLASSIFIER_PATH, 'rb') as file:
    model, class_names = pickle.load(file)

with tf.compat.v1.Graph().as_default():
    gpu_options = tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.6)
    sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options,
                                                                log_device_placement=False))
    with sess.as_default():
        # Load the model
        # print('Loading feature extraction model')
        facenet.load_model(FACENET_MODEL_PATH)

        # Get input and output tensors
        images_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("input:0")
        embeddings = tf.compat.v1.get_default_graph().get_tensor_by_name("embeddings:0")
        phase_train_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("phase_train:0")
        embedding_size = embeddings.get_shape()[1]

        pnet, rnet, onet = detect_face.create_mtcnn(sess, '')
        people_detected = set()
        person_detected = collections.Counter()


# endregion


def run_model(frame):
    frame = imutils.resize(frame, width=600)
    frame = cv2.flip(frame, 1)
    bounding_boxes, _ = detect_face.detect_face(frame, MINSIZE, pnet, rnet, onet, THRESHOLD, FACTOR)
    columnIndex = 0

    # Sort 2D numpy array by 2nd Column
    bounding_boxes = bounding_boxes[bounding_boxes[:, columnIndex].argsort()]
    faces_found = bounding_boxes.shape[0]

    NumberOfPeople.get_num = faces_found
    if NumberOfPeople.get_num == 0:
        # clear array
        Name.final_name.clear()
        Name.final_name = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        Statistics.array.clear()
        Statistics.array = [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [],
                            [], [], []]
        Statistics.index.clear()
        Statistics.index = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    try:
        if faces_found > 0:
            det = bounding_boxes[:, 0:4]
            bb = np.zeros((faces_found, 4), dtype=np.int32)

            # count number of people on frame, start with person 0
            for i in range(faces_found):
                bb[i][0] = det[i][0]
                bb[i][1] = det[i][1]
                bb[i][2] = det[i][2]
                bb[i][3] = det[i][3]

                if 0.15 < (bb[i][3] - bb[i][1]) / frame.shape[0] < 0.3:
                    cropped = frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :]
                    scaled = cv2.resize(cropped, (INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE), interpolation=cv2.INTER_CUBIC)
                    scaled = facenet.prewhiten(scaled)
                    scaled_reshape = scaled.reshape(-1, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE, 3)
                    feed_dict = {images_placeholder: scaled_reshape, phase_train_placeholder: False}
                    emb_array = sess.run(embeddings, feed_dict=feed_dict)
                    predictions = model.predict_proba(emb_array)
                    best_class_indices = np.argmax(predictions, axis=1)
                    best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]

                    best_name = class_names[best_class_indices[0]]

                    # insert 10 values to array
                    if Statistics.index[i] < 10:
                        try:
                            Statistics.array[i].pop(Statistics.index[i])
                            Statistics.array[i].insert(Statistics.index[i], (best_name,
                                                                             float(best_class_probabilities)))
                            Statistics.index[i] += 1
                        except IndexError:
                            Statistics.array[i].insert(Statistics.index[0], (best_name,
                                                                             float(best_class_probabilities)))
                            Statistics.index[i] += 1
                    else:
                        Statistics.array[i].pop(0)
                        Statistics.array[i].insert(0, (best_name, best_class_probabilities))
                        Statistics.index[i] = 1

                    # enough 10 values
                    if len(Statistics.array[i]) == 10:
                        new = [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []]
                        resultname = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                        row_sort = sorted(Statistics.array[i])
                        x = 0
                        cal = 0
                        # split array after recognizing
                        while row_sort:
                            if len(row_sort) == 1:
                                new[x].insert(0, row_sort[0])
                                x += 1
                                break

                            for z in range(1, 100):
                                try:
                                    if row_sort[0][0] != row_sort[z][0]:
                                        for k in range(0, z):
                                            new[x].insert(k, row_sort[k])
                                        for k in range(0, z):
                                            row_sort.pop(0)
                                        break
                                except IndexError:
                                    for k in range(0, z):
                                        new[x].insert(k, row_sort[k])
                                    for k in range(0, z):
                                        row_sort.pop(0)
                                    break
                            x += 1

                        # calculate
                        for z in range(0, x):
                            for k in range(0, len(new[z])):
                                cal += new[z][k][1]
                            cal = cal / len(new[z])
                            cal = cal * (len(new[z]) / 10)
                            new[z].insert(0, new[z][0][0])
                            new[z].insert(1, cal)
                            resultname.insert(z, cal)
                            cal = 0

                        # compare
                        for z in range(0, x):
                            if max(resultname) == new[z][1]:
                                Name.final_name[i] = new[z][0]
                                probabilities.result = max(resultname)

                        if Name.final_name[i] == "unknown":
                            cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 0, 255), 2)
                            text_x = bb[i][0]
                            text_y = bb[i][3] + 20
                            cv2.putText(frame, "Unknown", (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                        1, (255, 255, 255), thickness=1, lineType=2)
                        else:
                            cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0), 2)
                            text_x = bb[i][0]
                            text_y = bb[i][3] + 20
                            cv2.putText(frame, "{}_{}".format(Name.final_name[i], i), (text_x, text_y),
                                        cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                        1, (255, 255, 255), thickness=1, lineType=2)
    except:
        pass
    return frame


"""
example:
    + Statistics.array[][]:
        row 0; column [0-9] (person 0): [Hien, 0,86], [Triet, 0,46], [Unknown, 0,3], .... , [Hien, 0,86]
        row 1; column [0-9] (person 1): [Tri, 0,86], [Triet, 0,46], [Tri, 0,3], .... , [Tri, 0,86]
    + Statistics.index[]:
        1 row; n column: [index[0], index[1], ....... , index[n]] (n people)
"""
