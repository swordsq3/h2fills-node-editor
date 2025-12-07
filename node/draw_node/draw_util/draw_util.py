import copy
import math
from collections import Counter
from typing import List, Dict, Tuple

import cv2
import numpy as np


def draw_info(node_name, node_result, image):
    classification_nodes = ['Classification']
    object_detection_nodes = ['ObjectDetection']
    wholebody_detection_nodes = ['WholebodyDetection']
    semantic_segmentation_nodes = ['SemanticSegmentation']
    pose_estimation_nodes = ['PoseEstimation']
    face_detection_nodes = ['FaceDetection']
    multi_object_tracking_nodes = ['MultiObjectTracking']
    qr_code_detection_nodes = ['QRCodeDetection']

    debug_image = copy.deepcopy(image)
    if node_name in classification_nodes:
        use_object_detection = node_result.get('use_object_detection', [])
        class_ids = node_result.get('class_ids', [])
        class_scores = node_result.get('class_scores', [])
        class_names = node_result.get('class_names', [])

        if use_object_detection:
            od_bboxes = node_result.get('od_bboxes', [])
            od_scores = node_result.get('od_scores', [])
            od_class_ids = node_result.get('od_class_ids', [])
            od_class_names = node_result.get('od_class_names', [])
            od_score_th = node_result.get('od_score_th', [])
            debug_image = draw_classification_with_od_info(
                debug_image,
                class_ids,
                class_scores,
                class_names,
                od_bboxes,
                od_scores,
                od_class_ids,
                od_class_names,
                od_score_th,
                thickness=3,
            )
        else:
            debug_image = draw_classification_info(
                debug_image,
                class_ids,
                class_scores,
                class_names,
            )
    elif node_name in object_detection_nodes:
        # Wholebody34の結果かどうかを判定（boxesキーがあればWholebody34）
        if 'boxes' in node_result:
            boxes = node_result.get('boxes', [])
            enable_bone_drawing = node_result.get('enable_bone_drawing', False)
            disable_gender_identification = node_result.get('disable_gender_identification', False)
            disable_headpose_identification = node_result.get('disable_headpose_identification', False)
            disable_left_right_hand_identification = node_result.get('disable_left_right_hand_identification', False)
            debug_image = draw_wholebody34_detection_info(
                debug_image,
                boxes,
                enable_bone_drawing=enable_bone_drawing,
                disable_gender_identification=disable_gender_identification,
                disable_headpose_identification=disable_headpose_identification,
                disable_left_right_hand_identification=disable_left_right_hand_identification,
            )
        else:
            bboxes = node_result.get('bboxes', [])
            scores = node_result.get('scores', [])
            class_ids = node_result.get('class_ids', [])
            class_names = node_result.get('class_names', [])
            score_th = node_result.get('score_th', [])
            debug_image = draw_object_detection_info(
                debug_image,
                score_th,
                bboxes,
                scores,
                class_ids,
                class_names,
            )
    elif node_name in wholebody_detection_nodes:
        boxes = node_result.get('boxes', [])
        enable_bone_drawing = node_result.get('enable_bone_drawing', False)
        disable_gender_identification = node_result.get('disable_gender_identification', False)
        disable_headpose_identification = node_result.get('disable_headpose_identification', False)
        disable_left_right_hand_identification = node_result.get('disable_left_right_hand_identification', False)
        debug_image = draw_wholebody34_detection_info(
            debug_image,
            boxes,
            enable_bone_drawing=enable_bone_drawing,
            disable_gender_identification=disable_gender_identification,
            disable_headpose_identification=disable_headpose_identification,
            disable_left_right_hand_identification=disable_left_right_hand_identification,
        )
    elif node_name in semantic_segmentation_nodes:
        class_num = node_result.get('class_num', [])
        segmentation_map = node_result.get('segmentation_map', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_semantic_segmentation_info(
            debug_image,
            score_th,
            class_num,
            segmentation_map,
        )
    elif node_name in pose_estimation_nodes:
        model_name = node_result.get('model_name', [])
        results_list = node_result.get('results_list', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_pose_estimation_info(
            model_name,
            debug_image,
            results_list,
            score_th,
        )
    elif node_name in face_detection_nodes:
        model_name = node_result.get('model_name', [])
        results_list = node_result.get('results_list', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_face_detection_info(
            model_name,
            debug_image,
            results_list,
            score_th,
        )
    elif node_name in multi_object_tracking_nodes:
        track_ids = node_result.get('track_ids', [])
        bboxes = node_result.get('bboxes', [])
        scores = node_result.get('scores', [])
        class_ids = node_result.get('class_ids', [])
        class_names = node_result.get('class_names', [])
        track_id_dict = node_result.get('track_id_dict', [])
        debug_image = draw_multi_object_tracking_info(
            debug_image,
            track_ids,
            bboxes,
            scores,
            class_ids,
            class_names,
            track_id_dict,
        )
    elif node_name in qr_code_detection_nodes:
        texts = node_result.get('texts', [])
        bboxes = node_result.get('bboxes', [])
        debug_image = draw_qrcode_detection_info(
            debug_image,
            texts,
            bboxes,
        )

    return debug_image


def get_color(index):
    temp_index = abs(int(index + 35)) * 3
    color = (
        (29 * temp_index) % 255,
        (17 * temp_index) % 255,
        (37 * temp_index) % 255,
    )
    return color


def get_color_map_list(num_classes, custom_color=None):
    num_classes += 1
    color_map = num_classes * [0, 0, 0]
    for i in range(0, num_classes):
        j = 0
        lab = i
        while lab:
            color_map[i * 3 + 2] |= (((lab >> 0) & 1) << (7 - j))
            color_map[i * 3 + 1] |= (((lab >> 1) & 1) << (7 - j))
            color_map[i * 3] |= (((lab >> 2) & 1) << (7 - j))
            j += 1
            lab >>= 3
    color_map = color_map[3:]

    if custom_color:
        color_map[:len(custom_color)] = custom_color
    return color_map


def draw_classification_info(
    image,
    class_ids,
    class_scores,
    class_names,
):
    debug_image = copy.deepcopy(image)
    for index, (class_score,
                class_id) in enumerate(zip(class_scores, class_ids)):
        score = '%.2f' % class_score
        text = '%s:%s(%s)' % (str(class_id), str(
            class_names[int(class_id)]), score)
        debug_image = cv2.putText(
            debug_image,
            text,
            (15, 30 + (index * 35)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            thickness=3,
        )

    return debug_image


def draw_object_detection_info(
    image,
    score_th,
    bboxes,
    scores,
    class_ids,
    class_names,
    thickness=3,
):
    debug_image = copy.deepcopy(image)

    for bbox, score, class_id in zip(bboxes, scores, class_ids):
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

        if score_th > score:
            continue

        color = get_color(class_id)

        # バウンディングボックス
        debug_image = cv2.rectangle(
            debug_image,
            (x1, y1),
            (x2, y2),
            color,
            thickness=thickness,
        )

        # クラスID、スコア
        score = '%.2f' % score
        text = '%s:%s(%s)' % (int(class_id), str(
            class_names[int(class_id)]), score)
        debug_image = cv2.putText(
            debug_image,
            text,
            (x1, y1 - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=thickness,
        )

    return debug_image


def draw_classification_with_od_info(
    image,
    class_id_list,
    score_list,
    class_name_dict,
    od_bboxes,
    od_scores,
    od_class_ids,
    od_class_names,
    od_score_th,
    thickness=3,
):
    debug_image = copy.deepcopy(image)

    for class_id, score, od_bbox, od_score, od_class_id in zip(
            class_id_list,
            score_list,
            od_bboxes,
            od_scores,
            od_class_ids,
    ):
        x1, y1 = int(od_bbox[0]), int(od_bbox[1])
        x2, y2 = int(od_bbox[2]), int(od_bbox[3])

        if od_score_th > od_score:
            continue

        color = get_color(od_class_id)

        # バウンディングボックス
        debug_image = cv2.rectangle(
            debug_image,
            (x1, y1),
            (x2, y2),
            color,
            thickness=thickness,
        )

        # Object Detection：クラスID、スコア
        score_text = '%.2f' % od_score
        text = '%s:%s(%s)' % (int(od_class_id),
                              str(od_class_names[int(od_class_id)]),
                              score_text)
        debug_image = cv2.putText(
            debug_image,
            'Detection(' + text + ')',
            (x1, y1 - 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=thickness,
        )

        # Classification：クラスID、スコア
        score_text = '%.2f' % score
        text = '%s:%s(%s)' % (int(class_id), str(
            class_name_dict[int(class_id)]), score_text)
        debug_image = cv2.putText(
            debug_image,
            'Classification(' + text + ')',
            (x1, y1 - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=thickness,
        )

    return debug_image


def draw_semantic_segmentation_info(
    image,
    score_th,
    class_num,
    segmentation_map,
):
    debug_image = copy.deepcopy(image)

    segmentation_map = np.where(segmentation_map > score_th, 0, 1)

    # color map list
    color_map = get_color_map_list(class_num)

    for index, mask in enumerate(segmentation_map):
        bg_image = np.zeros(image.shape, dtype=np.uint8)
        bg_image[:] = (color_map[index * 3 + 0], color_map[index * 3 + 1],
                       color_map[index * 3 + 2])

        mask = np.stack((mask, ) * 3, axis=-1).astype('uint8')

        mask_image = np.where(mask, debug_image, bg_image)
        debug_image = cv2.addWeighted(debug_image, 0.5, mask_image, 0.5, 1.0)

    return debug_image


def draw_pose_estimation_info(model_name, image, results_list, score_th):
    debug_image = copy.deepcopy(image)

    move_net_nodes = [
        'MoveNet(SinglePose Lightning)',
        'MoveNet(SinglePose Thunder)',
        'MoveNet(MulitPose Lightning)',
    ]
    mediapipe_hands_nodes = [
        'MediaPipe Hands(Complexity0)',
        'MediaPipe Hands(Complexity1)',
    ]
    mediapipe_pose_nodes = [
        'MediaPipe Pose(Complexity0)',
        'MediaPipe Pose(Complexity1)',
        'MediaPipe Pose(Complexity2)',
    ]

    if model_name in move_net_nodes:
        debug_image = draw_movenet_info(debug_image, results_list, score_th)
    elif model_name in mediapipe_hands_nodes:
        debug_image = draw_mediapipe_hands_info(debug_image, results_list)
    elif model_name in mediapipe_pose_nodes:
        debug_image = draw_mediapipe_pose_info(
            debug_image,
            results_list,
            score_th,
        )

    return debug_image


def draw_mediapipe_hands_info(image, results_list):
    for results in results_list:
        # キーポイント
        for id in range(21):
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # 接続線
        # 親指
        cv2.line(image, results[2][:2], results[3][:2], (0, 255, 0), 2)
        cv2.line(image, results[3][:2], results[4][:2], (0, 255, 0), 2)

        # 人差指
        cv2.line(image, results[5][:2], results[6][:2], (0, 255, 0), 2)
        cv2.line(image, results[6][:2], results[7][:2], (0, 255, 0), 2)
        cv2.line(image, results[7][:2], results[8][:2], (0, 255, 0), 2)

        # 中指
        cv2.line(image, results[9][:2], results[10][:2], (0, 255, 0), 2)
        cv2.line(image, results[10][:2], results[11][:2], (0, 255, 0), 2)
        cv2.line(image, results[11][:2], results[12][:2], (0, 255, 0), 2)

        # 薬指
        cv2.line(image, results[13][:2], results[14][:2], (0, 255, 0), 2)
        cv2.line(image, results[14][:2], results[15][:2], (0, 255, 0), 2)
        cv2.line(image, results[15][:2], results[16][:2], (0, 255, 0), 2)

        # 小指
        cv2.line(image, results[17][:2], results[18][:2], (0, 255, 0), 2)
        cv2.line(image, results[18][:2], results[19][:2], (0, 255, 0), 2)
        cv2.line(image, results[19][:2], results[20][:2], (0, 255, 0), 2)

        # 手の平
        cv2.line(image, results[0][:2], results[1][:2], (0, 255, 0), 2)
        cv2.line(image, results[1][:2], results[2][:2], (0, 255, 0), 2)
        cv2.line(image, results[2][:2], results[5][:2], (0, 255, 0), 2)
        cv2.line(image, results[5][:2], results[9][:2], (0, 255, 0), 2)
        cv2.line(image, results[9][:2], results[13][:2], (0, 255, 0), 2)
        cv2.line(image, results[13][:2], results[17][:2], (0, 255, 0), 2)
        cv2.line(image, results[17][:2], results[0][:2], (0, 255, 0), 2)

        cx, cy = results['palm_moment']
        cv2.putText(image, results['label'], (cx - 20, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    return image


def draw_mediapipe_pose_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(33):
            landmark_x, landmark_y = results[id][0], results[id][1]
            visibility = results[id][3]

            if score_th > visibility:
                continue
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # 接続線
        # 右目
        if results[1][3] > score_th and results[2][3] > score_th:
            cv2.line(image, results[1][:2], results[2][:2], (0, 255, 0), 2)
        if results[2][3] > score_th and results[3][3] > score_th:
            cv2.line(image, results[2][:2], results[3][:2], (0, 255, 0), 2)

        # 左目
        if results[4][3] > score_th and results[5][3] > score_th:
            cv2.line(image, results[4][:2], results[5][:2], (0, 255, 0), 2)
        if results[5][3] > score_th and results[6][3] > score_th:
            cv2.line(image, results[5][:2], results[6][:2], (0, 255, 0), 2)

        # 口
        if results[9][3] > score_th and results[10][3] > score_th:
            cv2.line(image, results[9][:2], results[10][:2], (0, 255, 0), 2)

        # 肩
        if results[11][3] > score_th and results[12][3] > score_th:
            cv2.line(image, results[11][:2], results[12][:2], (0, 255, 0), 2)

        # 右腕
        if results[11][3] > score_th and results[13][3] > score_th:
            cv2.line(image, results[11][:2], results[13][:2], (0, 255, 0), 2)
        if results[13][3] > score_th and results[15][3] > score_th:
            cv2.line(image, results[13][:2], results[15][:2], (0, 255, 0), 2)

        # 左腕
        if results[12][3] > score_th and results[14][3] > score_th:
            cv2.line(image, results[12][:2], results[14][:2], (0, 255, 0), 2)
        if results[14][3] > score_th and results[16][3] > score_th:
            cv2.line(image, results[14][:2], results[16][:2], (0, 255, 0), 2)

        # 右手
        if results[15][3] > score_th and results[17][3] > score_th:
            cv2.line(image, results[15][:2], results[17][:2], (0, 255, 0), 2)
        if results[17][3] > score_th and results[19][3] > score_th:
            cv2.line(image, results[17][:2], results[19][:2], (0, 255, 0), 2)
        if results[19][3] > score_th and results[21][3] > score_th:
            cv2.line(image, results[19][:2], results[21][:2], (0, 255, 0), 2)
        if results[21][3] > score_th and results[15][3] > score_th:
            cv2.line(image, results[21][:2], results[15][:2], (0, 255, 0), 2)

        # 左手
        if results[16][3] > score_th and results[18][3] > score_th:
            cv2.line(image, results[16][:2], results[18][:2], (0, 255, 0), 2)
        if results[18][3] > score_th and results[20][3] > score_th:
            cv2.line(image, results[18][:2], results[20][:2], (0, 255, 0), 2)
        if results[20][3] > score_th and results[22][3] > score_th:
            cv2.line(image, results[20][:2], results[22][:2], (0, 255, 0), 2)
        if results[22][3] > score_th and results[16][3] > score_th:
            cv2.line(image, results[22][:2], results[16][:2], (0, 255, 0), 2)

        # 胴体
        if results[11][3] > score_th and results[23][3] > score_th:
            cv2.line(image, results[11][:2], results[23][:2], (0, 255, 0), 2)
        if results[12][3] > score_th and results[24][3] > score_th:
            cv2.line(image, results[12][:2], results[24][:2], (0, 255, 0), 2)
        if results[23][3] > score_th and results[24][3] > score_th:
            cv2.line(image, results[23][:2], results[24][:2], (0, 255, 0), 2)

        # 右足
        if results[23][3] > score_th and results[25][3] > score_th:
            cv2.line(image, results[23][:2], results[25][:2], (0, 255, 0), 2)
        if results[25][3] > score_th and results[27][3] > score_th:
            cv2.line(image, results[25][:2], results[27][:2], (0, 255, 0), 2)
        if results[27][3] > score_th and results[29][3] > score_th:
            cv2.line(image, results[27][:2], results[29][:2], (0, 255, 0), 2)
        if results[29][3] > score_th and results[31][3] > score_th:
            cv2.line(image, results[29][:2], results[31][:2], (0, 255, 0), 2)

        # 左足
        if results[24][3] > score_th and results[26][3] > score_th:
            cv2.line(image, results[24][:2], results[26][:2], (0, 255, 0), 2)
        if results[26][3] > score_th and results[28][3] > score_th:
            cv2.line(image, results[26][:2], results[28][:2], (0, 255, 0), 2)
        if results[28][3] > score_th and results[30][3] > score_th:
            cv2.line(image, results[28][:2], results[30][:2], (0, 255, 0), 2)
        if results[30][3] > score_th and results[32][3] > score_th:
            cv2.line(image, results[30][:2], results[32][:2], (0, 255, 0), 2)
    return image


def draw_movenet_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(17):
            landmark_x, landmark_y = results[id][0], results[id][1]
            visibility = results[id][2]

            if score_th > visibility:
                continue
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # Line：鼻 → 左目
        if results[0][2] > score_th and results[1][2] > score_th:
            cv2.line(image, results[0][:2], results[1][:2], (0, 255, 0), 2)
        # Line：鼻 → 右目
        if results[0][2] > score_th and results[2][2] > score_th:
            cv2.line(image, results[0][:2], results[2][:2], (0, 255, 0), 2)
        # Line：左目 → 左耳
        if results[1][2] > score_th and results[3][2] > score_th:
            cv2.line(image, results[1][:2], results[3][:2], (0, 255, 0), 2)
        # Line：右目 → 右耳
        if results[2][2] > score_th and results[4][2] > score_th:
            cv2.line(image, results[2][:2], results[4][:2], (0, 255, 0), 2)
        # Line：左肩 → 右肩
        if results[5][2] > score_th and results[6][2] > score_th:
            cv2.line(image, results[5][:2], results[6][:2], (0, 255, 0), 2)
        # Line：左肩 → 左肘
        if results[5][2] > score_th and results[7][2] > score_th:
            cv2.line(image, results[5][:2], results[7][:2], (0, 255, 0), 2)
        # Line：左肘 → 左手首
        if results[7][2] > score_th and results[9][2] > score_th:
            cv2.line(image, results[7][:2], results[9][:2], (0, 255, 0), 2)
        # Line：右肩 → 右肘
        if results[6][2] > score_th and results[8][2] > score_th:
            cv2.line(image, results[6][:2], results[8][:2], (0, 255, 0), 2)
        # Line：右肘 → 右手首
        if results[8][2] > score_th and results[10][2] > score_th:
            cv2.line(image, results[8][:2], results[10][:2], (0, 255, 0), 2)
        # Line：左股関節 → 右股関節
        if results[11][2] > score_th and results[12][2] > score_th:
            cv2.line(image, results[11][:2], results[12][:2], (0, 255, 0), 2)
        # Line：左肩 → 左股関節
        if results[5][2] > score_th and results[11][2] > score_th:
            cv2.line(image, results[5][:2], results[11][:2], (0, 255, 0), 2)
        # Line：左股関節 → 左ひざ
        if results[11][2] > score_th and results[13][2] > score_th:
            cv2.line(image, results[11][:2], results[13][:2], (0, 255, 0), 2)
        # Line：左ひざ → 左足首
        if results[13][2] > score_th and results[15][2] > score_th:
            cv2.line(image, results[13][:2], results[15][:2], (0, 255, 0), 2)
        # Line：右肩 → 右股関節
        if results[6][2] > score_th and results[12][2] > score_th:
            cv2.line(image, results[6][:2], results[12][:2], (0, 255, 0), 2)
        # Line：右股関節 → 右ひざ
        if results[12][2] > score_th and results[14][2] > score_th:
            cv2.line(image, results[12][:2], results[14][:2], (0, 255, 0), 2)
        # Line：右ひざ → 右足首
        if results[14][2] > score_th and results[16][2] > score_th:
            cv2.line(image, results[14][:2], results[16][:2], (0, 255, 0), 2)

        bbox = results.get('bbox', None)
        if bbox is not None:
            if bbox[4] > score_th:
                image = cv2.rectangle(
                    image,
                    (bbox[0], bbox[1]),
                    (bbox[2], bbox[3]),
                    (0, 255, 0),
                    thickness=2,
                )

    return image


def draw_face_detection_info(model_name, image, results_list, score_th):
    debug_image = copy.deepcopy(image)

    if model_name == 'MediaPipe FaceDetection(~2m)' or \
            model_name == 'MediaPipe FaceDetection(~5m)':
        debug_image = draw_mediapipe_face_detection_info(
            debug_image,
            results_list,
            score_th,
        )
    elif model_name == 'MediaPipe FaceMesh' or \
            model_name == 'MediaPipe FaceMesh(Refine Landmark)':
        debug_image = draw_mediapipe_facemesh_info(
            debug_image,
            results_list,
            score_th,
        )
    elif model_name == 'YuNet':
        debug_image = draw_yunet_info(
            debug_image,
            results_list,
            score_th,
        )

    return debug_image


def draw_mediapipe_face_detection_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(6):
            if score_th > results[id][2]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # バウンディングボックス
        bbox = results.get('bbox', None)
        if bbox is not None:
            image = cv2.rectangle(
                image,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (0, 255, 0),
                thickness=2,
            )

    return image


def draw_mediapipe_facemesh_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(len(results)):
            if score_th > results[id][3]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 2, (0, 255, 0), -1)

        # 左眉毛(55：内側、46：外側)
        cv2.line(image, results[55][:2], results[65][:2], (0, 255, 0), 2)
        cv2.line(image, results[65][:2], results[52][:2], (0, 255, 0), 2)
        cv2.line(image, results[52][:2], results[53][:2], (0, 255, 0), 2)
        cv2.line(image, results[53][:2], results[46][:2], (0, 255, 0), 2)

        # # 右眉毛(285：内側、276：外側)
        cv2.line(image, results[285][:2], results[295][:2], (0, 255, 0), 2)
        cv2.line(image, results[295][:2], results[282][:2], (0, 255, 0), 2)
        cv2.line(image, results[282][:2], results[283][:2], (0, 255, 0), 2)
        cv2.line(image, results[283][:2], results[276][:2], (0, 255, 0), 2)

        # # 左目 (133：目頭、246：目尻)
        cv2.line(image, results[133][:2], results[173][:2], (0, 255, 0), 2)
        cv2.line(image, results[173][:2], results[157][:2], (0, 255, 0), 2)
        cv2.line(image, results[157][:2], results[158][:2], (0, 255, 0), 2)
        cv2.line(image, results[158][:2], results[159][:2], (0, 255, 0), 2)
        cv2.line(image, results[159][:2], results[160][:2], (0, 255, 0), 2)
        cv2.line(image, results[160][:2], results[161][:2], (0, 255, 0), 2)
        cv2.line(image, results[161][:2], results[246][:2], (0, 255, 0), 2)

        cv2.line(image, results[246][:2], results[163][:2], (0, 255, 0), 2)
        cv2.line(image, results[163][:2], results[144][:2], (0, 255, 0), 2)
        cv2.line(image, results[144][:2], results[145][:2], (0, 255, 0), 2)
        cv2.line(image, results[145][:2], results[153][:2], (0, 255, 0), 2)
        cv2.line(image, results[153][:2], results[154][:2], (0, 255, 0), 2)
        cv2.line(image, results[154][:2], results[155][:2], (0, 255, 0), 2)
        cv2.line(image, results[155][:2], results[133][:2], (0, 255, 0), 2)

        # # 右目 (362：目頭、466：目尻)
        cv2.line(image, results[362][:2], results[398][:2], (0, 255, 0), 2)
        cv2.line(image, results[398][:2], results[384][:2], (0, 255, 0), 2)
        cv2.line(image, results[384][:2], results[385][:2], (0, 255, 0), 2)
        cv2.line(image, results[385][:2], results[386][:2], (0, 255, 0), 2)
        cv2.line(image, results[386][:2], results[387][:2], (0, 255, 0), 2)
        cv2.line(image, results[387][:2], results[388][:2], (0, 255, 0), 2)
        cv2.line(image, results[388][:2], results[466][:2], (0, 255, 0), 2)

        cv2.line(image, results[466][:2], results[390][:2], (0, 255, 0), 2)
        cv2.line(image, results[390][:2], results[373][:2], (0, 255, 0), 2)
        cv2.line(image, results[373][:2], results[374][:2], (0, 255, 0), 2)
        cv2.line(image, results[374][:2], results[380][:2], (0, 255, 0), 2)
        cv2.line(image, results[380][:2], results[381][:2], (0, 255, 0), 2)
        cv2.line(image, results[381][:2], results[382][:2], (0, 255, 0), 2)
        cv2.line(image, results[382][:2], results[362][:2], (0, 255, 0), 2)

        # # 口 (308：右端、78：左端)
        cv2.line(image, results[308][:2], results[415][:2], (0, 255, 0), 2)
        cv2.line(image, results[415][:2], results[310][:2], (0, 255, 0), 2)
        cv2.line(image, results[310][:2], results[311][:2], (0, 255, 0), 2)
        cv2.line(image, results[311][:2], results[312][:2], (0, 255, 0), 2)
        cv2.line(image, results[312][:2], results[13][:2], (0, 255, 0), 2)
        cv2.line(image, results[13][:2], results[82][:2], (0, 255, 0), 2)
        cv2.line(image, results[82][:2], results[81][:2], (0, 255, 0), 2)
        cv2.line(image, results[81][:2], results[80][:2], (0, 255, 0), 2)
        cv2.line(image, results[80][:2], results[191][:2], (0, 255, 0), 2)
        cv2.line(image, results[191][:2], results[78][:2], (0, 255, 0), 2)

        cv2.line(image, results[78][:2], results[95][:2], (0, 255, 0), 2)
        cv2.line(image, results[95][:2], results[88][:2], (0, 255, 0), 2)
        cv2.line(image, results[88][:2], results[178][:2], (0, 255, 0), 2)
        cv2.line(image, results[178][:2], results[87][:2], (0, 255, 0), 2)
        cv2.line(image, results[87][:2], results[14][:2], (0, 255, 0), 2)
        cv2.line(image, results[14][:2], results[317][:2], (0, 255, 0), 2)
        cv2.line(image, results[317][:2], results[402][:2], (0, 255, 0), 2)
        cv2.line(image, results[402][:2], results[318][:2], (0, 255, 0), 2)
        cv2.line(image, results[318][:2], results[324][:2], (0, 255, 0), 2)
        cv2.line(image, results[324][:2], results[308][:2], (0, 255, 0), 2)

    return image


def draw_yunet_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(5):
            if score_th > results[id][2]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # バウンディングボックス
        bbox = results.get('bbox', None)
        if bbox is not None:
            image = cv2.rectangle(
                image,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (0, 255, 0),
                thickness=2,
            )

    return image


def draw_multi_object_tracking_info(
    image,
    track_ids,
    bboxes,
    scores,
    class_ids,
    class_names,
    track_id_dict,
):
    for id, bbox, score, class_id in zip(track_ids, bboxes, scores, class_ids):
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

        color = get_color(track_id_dict[id])

        # バウンディングボックス
        image = cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            color,
            thickness=2,
        )

        # トラックID、スコア
        score = '%.2f' % score
        text = 'TID:%s(%s)' % (str(int(track_id_dict[id])), str(score))
        image = cv2.putText(
            image,
            text,
            (x1, y1 - 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=2,
        )

        # クラスID
        text = 'CID:%s(%s)' % (str(int(class_id)), class_names[int(class_id)])
        image = cv2.putText(
            image,
            text,
            (x1, y1 - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=2,
        )

    return image


def draw_qrcode_detection_info(
    image,
    texts,
    bboxes,
):
    for text, bbox in zip(texts, bboxes):
        # 各辺
        cv2.line(image, (bbox[0][0], bbox[0][1]), (bbox[1][0], bbox[1][1]),
                 (255, 0, 0), 2)
        cv2.line(image, (bbox[1][0], bbox[1][1]), (bbox[2][0], bbox[2][1]),
                 (255, 0, 0), 2)
        cv2.line(image, (bbox[2][0], bbox[2][1]), (bbox[3][0], bbox[3][1]),
                 (0, 255, 0), 2)
        cv2.line(image, (bbox[3][0], bbox[3][1]), (bbox[0][0], bbox[0][1]),
                 (0, 255, 0), 2)

        # テキスト
        cv2.putText(
            image,
            str(text),
            (bbox[0][0], bbox[0][1] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            thickness=3,
        )

    return image


# Head pose colors (BGR format)
_HEAD_POSE_COLORS = {
    0: (216, 67, 21),   # Front
    1: (255, 87, 34),   # Right-Front
    2: (123, 31, 162),  # Right-Side
    3: (255, 193, 7),   # Right-Back
    4: (76, 175, 80),   # Back
    5: (33, 150, 243),  # Left-Back
    6: (156, 39, 176),  # Left-Side
    7: (0, 188, 212),   # Left-Front
}

_HEAD_POSE_NAMES = {
    0: "Front",
    1: "Right-Front",
    2: "Right-Side",
    3: "Right-Back",
    4: "Back",
    5: "Left-Back",
    6: "Left-Side",
    7: "Left-Front",
}

# Skeleton edges
_WHOLEBODY34_EDGES = [
    (21, 22), (21, 22),  # collarbone -> shoulder
    (21, 23),            # collarbone -> solar_plexus
    (22, 24), (22, 24),  # shoulder -> elbow
    (22, 30), (22, 30),  # shoulder -> hip_joint
    (24, 25), (24, 25),  # elbow -> wrist
    (23, 29),            # solar_plexus -> abdomen
    (29, 30), (29, 30),  # abdomen -> hip_joint
    (30, 31), (30, 31),  # hip_joint -> knee
    (31, 32), (31, 32),  # knee -> ankle
]


def _draw_dashed_line(
    image: np.ndarray,
    pt1: Tuple[int, int],
    pt2: Tuple[int, int],
    color: Tuple[int, int, int],
    thickness: int = 1,
    dash_length: int = 10,
):
    dist = ((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2) ** 0.5
    dashes = int(dist / dash_length)
    if dashes == 0:
        cv2.line(image, pt1, pt2, color, thickness)
        return
    for i in range(dashes):
        start = (
            int(pt1[0] + (pt2[0] - pt1[0]) * i / dashes),
            int(pt1[1] + (pt2[1] - pt1[1]) * i / dashes)
        )
        end = (
            int(pt1[0] + (pt2[0] - pt1[0]) * (i + 0.5) / dashes),
            int(pt1[1] + (pt2[1] - pt1[1]) * (i + 0.5) / dashes)
        )
        cv2.line(image, start, end, color, thickness)


def _draw_dashed_rectangle(
    image: np.ndarray,
    top_left: Tuple[int, int],
    bottom_right: Tuple[int, int],
    color: Tuple[int, int, int],
    thickness: int = 1,
    dash_length: int = 10
):
    tl_tr = (bottom_right[0], top_left[1])
    bl_br = (top_left[0], bottom_right[1])
    _draw_dashed_line(image, top_left, tl_tr, color, thickness, dash_length)
    _draw_dashed_line(image, tl_tr, bottom_right, color, thickness, dash_length)
    _draw_dashed_line(image, bottom_right, bl_br, color, thickness, dash_length)
    _draw_dashed_line(image, bl_br, top_left, color, thickness, dash_length)


def _draw_wholebody34_skeleton(
    image: np.ndarray,
    boxes: List,
    color: Tuple[int, int, int] = (0, 255, 255),
    max_dist_threshold: float = 300.0,
):
    # Assign person_id to person boxes (classid=0)
    person_boxes = [b for b in boxes if b['classid'] == 0]
    for i, pbox in enumerate(person_boxes):
        pbox['person_id'] = i

    # Assign keypoints to person boxes
    keypoint_ids = {21, 22, 23, 24, 25, 29, 30, 31, 32}
    for box in boxes:
        if box['classid'] in keypoint_ids:
            box['person_id'] = -1
            for pbox in person_boxes:
                if (pbox['x1'] <= box['cx'] <= pbox['x2']) and (pbox['y1'] <= box['cy'] <= pbox['y2']):
                    box['person_id'] = pbox['person_id']
                    break

    # Group boxes by classid
    classid_to_boxes: Dict[int, List] = {}
    for b in boxes:
        classid_to_boxes.setdefault(b['classid'], []).append(b)

    edge_counts = Counter(_WHOLEBODY34_EDGES)
    lines_to_draw = []

    for (pid, cid), repeat_count in edge_counts.items():
        parent_list = classid_to_boxes.get(pid, [])
        child_list = classid_to_boxes.get(cid, [])

        if not parent_list or not child_list:
            continue

        for_parent = repeat_count if (pid in [21, 29]) else 1
        parent_capacity = [for_parent] * len(parent_list)
        child_used = [False] * len(child_list)

        pair_candidates = []
        for i, pbox in enumerate(parent_list):
            for j, cbox in enumerate(child_list):
                if (pbox.get('person_id') is not None and
                    cbox.get('person_id') is not None and
                    pbox['person_id'] == cbox['person_id']):
                    dist = math.hypot(pbox['cx'] - cbox['cx'], pbox['cy'] - cbox['cy'])
                    if dist <= max_dist_threshold:
                        pair_candidates.append((dist, i, j))

        pair_candidates.sort(key=lambda x: x[0])

        for dist, i, j in pair_candidates:
            if parent_capacity[i] > 0 and (not child_used[j]):
                pbox = parent_list[i]
                cbox = child_list[j]
                lines_to_draw.append(((pbox['cx'], pbox['cy']), (cbox['cx'], cbox['cy'])))
                parent_capacity[i] -= 1
                child_used[j] = True

    for (pt1, pt2) in lines_to_draw:
        cv2.line(image, pt1, pt2, color, thickness=2)


def draw_wholebody34_detection_info(
    image: np.ndarray,
    boxes: List,
    enable_bone_drawing: bool = False,
    disable_gender_identification: bool = False,
    disable_headpose_identification: bool = False,
    disable_left_right_hand_identification: bool = False,
    line_width: int = 2,
):
    debug_image = copy.deepcopy(image)
    debug_image_h = debug_image.shape[0]
    debug_image_w = debug_image.shape[1]

    white_line_width = line_width
    colored_line_width = line_width - 1 if line_width > 1 else 1

    for box in boxes:
        classid = box['classid']
        color = (255, 255, 255)

        # Determine color based on classid and attributes
        if classid == 0:  # Body
            if not disable_gender_identification:
                if box.get('gender') == 0:  # Male
                    color = (255, 0, 0)
                elif box.get('gender') == 1:  # Female
                    color = (139, 116, 225)
                else:
                    color = (0, 200, 255)
            else:
                color = (0, 200, 255)
        elif classid == 5:  # Body-With-Wheelchair
            color = (0, 200, 255)
        elif classid == 6:  # Body-With-Crutches
            color = (83, 36, 179)
        elif classid == 7:  # Head
            if not disable_headpose_identification:
                head_pose = box.get('head_pose', -1)
                color = _HEAD_POSE_COLORS.get(head_pose, (216, 67, 21))
            else:
                color = (0, 0, 255)
        elif classid == 16:  # Face
            color = (0, 200, 255)
        elif classid == 17:  # Eye
            color = (255, 0, 0)
        elif classid == 18:  # Nose
            color = (0, 255, 0)
        elif classid == 19:  # Mouth
            color = (0, 0, 255)
        elif classid == 20:  # Ear
            color = (203, 192, 255)
        elif classid == 21:  # Collarbone
            color = (0, 0, 255)
        elif classid == 22:  # Shoulder
            color = (255, 0, 0)
        elif classid == 23:  # Solar_plexus
            color = (252, 189, 107)
        elif classid == 24:  # Elbow
            color = (0, 255, 0)
        elif classid == 25:  # Wrist
            color = (0, 0, 255)
        elif classid == 26:  # Hand
            if not disable_left_right_hand_identification:
                if box.get('handedness') == 0:  # Left
                    color = (0, 128, 0)
                elif box.get('handedness') == 1:  # Right
                    color = (255, 0, 255)
                else:
                    color = (0, 255, 0)
            else:
                color = (0, 255, 0)
        elif classid == 29:  # Abdomen
            color = (0, 0, 255)
        elif classid == 30:  # Hip_joint
            color = (255, 0, 0)
        elif classid == 31:  # Knee
            color = (0, 0, 255)
        elif classid == 32:  # Ankle
            color = (255, 0, 0)
        elif classid == 33:  # Foot
            color = (250, 0, 136)

        x1, y1 = box['x1'], box['y1']
        x2, y2 = box['x2'], box['y2']
        cx, cy = box['cx'], box['cy']

        # Draw based on classid
        if classid in [21, 22, 23, 24, 25, 29, 30, 31, 32]:
            # Keypoints - draw as dots
            cv2.circle(debug_image, (cx, cy), 4, (255, 255, 255), -1)
            cv2.circle(debug_image, (cx, cy), 3, color, -1)
        elif classid == 0:  # Body
            if not disable_gender_identification and box.get('gender', -1) == -1:
                _draw_dashed_rectangle(debug_image, (x1, y1), (x2, y2), color, 2, 10)
            else:
                cv2.rectangle(debug_image, (x1, y1), (x2, y2), (255, 255, 255), white_line_width)
                cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, colored_line_width)
        elif classid == 7:  # Head
            if not disable_headpose_identification and box.get('head_pose', -1) == -1:
                _draw_dashed_rectangle(debug_image, (x1, y1), (x2, y2), color, 2, 10)
            else:
                cv2.rectangle(debug_image, (x1, y1), (x2, y2), (255, 255, 255), white_line_width)
                cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, colored_line_width)
        elif classid == 26:  # Hand
            if not disable_left_right_hand_identification and box.get('handedness', -1) == -1:
                _draw_dashed_rectangle(debug_image, (x1, y1), (x2, y2), color, 2, 10)
            else:
                cv2.rectangle(debug_image, (x1, y1), (x2, y2), (255, 255, 255), white_line_width)
                cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, colored_line_width)
        else:
            cv2.rectangle(debug_image, (x1, y1), (x2, y2), (255, 255, 255), white_line_width)
            cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, colored_line_width)

        # Draw attribute text for Body
        if classid == 0:
            generation_txt = ''
            generation = box.get('generation', -1)
            if generation == 0:
                generation_txt = 'Adult'
            elif generation == 1:
                generation_txt = 'Child'

            gender_txt = ''
            gender = box.get('gender', -1)
            if gender == 0:
                gender_txt = 'M'
            elif gender == 1:
                gender_txt = 'F'

            attr_txt = f'{generation_txt}({gender_txt})' if gender_txt else generation_txt

            if attr_txt:
                text_x = x1 if x1 + 50 < debug_image_w else debug_image_w - 50
                text_y = y1 - 10 if y1 - 25 > 0 else 20
                cv2.putText(debug_image, attr_txt, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(debug_image, attr_txt, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # Draw head pose text
        if classid == 7:
            head_pose = box.get('head_pose', -1)
            if head_pose != -1:
                headpose_txt = _HEAD_POSE_NAMES.get(head_pose, '')
                if headpose_txt:
                    text_x = x1 if x1 + 50 < debug_image_w else debug_image_w - 50
                    text_y = y1 - 10 if y1 - 25 > 0 else 20
                    cv2.putText(debug_image, headpose_txt, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(debug_image, headpose_txt, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # Draw handedness text
        if classid == 26:
            handedness = box.get('handedness', -1)
            handedness_txt = ''
            if handedness == 0:
                handedness_txt = 'L'
            elif handedness == 1:
                handedness_txt = 'R'
            if handedness_txt:
                text_x = x1 if x1 + 50 < debug_image_w else debug_image_w - 50
                text_y = y1 - 10 if y1 - 25 > 0 else 20
                cv2.putText(debug_image, handedness_txt, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(debug_image, handedness_txt, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    # Draw skeleton
    if enable_bone_drawing:
        _draw_wholebody34_skeleton(debug_image, boxes, color=(0, 255, 255), max_dist_threshold=300)

    return debug_image
