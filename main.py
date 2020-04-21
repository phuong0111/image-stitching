import os
import cv2
from matplotlib import pyplot as plt
import numpy as np
import random

dataset_name = "HW2_Dataset"
subsets = {}
orb = cv2.ORB_create()  # Initiate ORB detector
plt.style.use("ggplot")
plt.title(''), plt.xticks([]), plt.yticks([])
# each element needs to have 2-nearest neighbors, each list of descriptors needs to have more than 2 elements each
nearest_neighbor_num = 2    # TODO
ransac_thresh = 2.0
inlier_thresh = 5


def get_subset_names():
    root, directories, files = next(os.walk(dataset_name))
    for directory in sorted(directories):
        subsets[directory] = sorted(os.listdir(dataset_name + "/" + directory))


def main():
    for subset_name, subset_images_names in subsets.items():
        feature_points_plot = None
        panorama = cv2.imread(dataset_name + "/" + subset_name + '/' + subset_images_names[0])
        for i in range(0, len(subset_images_names) - 1):
            print(subset_images_names[i])

            # Read next images
            next_image = cv2.imread(dataset_name + "/" + subset_name + '/' + subset_images_names[i + 1])
            next_image = cv2.GaussianBlur(next_image, (3,3),0)
            next_image_gray = cv2.cvtColor(next_image, cv2.COLOR_BGR2GRAY)
            # next_image_gray = cv2.GaussianBlur(next_image_gray, (3,3),0)

            # Current image is the panorama
            cur_image = panorama
            cur_image = cv2.GaussianBlur(cur_image, (3,3),0)
            cur_image_gray = cv2.cvtColor(cur_image, cv2.COLOR_BGR2GRAY)
            # cur_image_gray = cv2.GaussianBlur(cur_image_gray, (3,3),0)

            # Feature extraction, feature matching, Homography finding, merging by transformation
            panorama = stitch_images(cur_image, cur_image_gray, next_image, next_image_gray, feature_points_plot)

        # Read ground truth panorama image
        ground_truth = cv2.imread(dataset_name + "/" + subset_name + '_gt.png')

        plt.imshow(panorama)
        plt.title(''), plt.xticks([]), plt.yticks([])
        plt.show()
        plt.imshow(ground_truth)
        plt.title(''), plt.xticks([]), plt.yticks([])
        plt.show()


def stitch_images(cur_image, cur_image_gray, next_image, next_image_gray, feature_points_plot):

    # Feature extraction
    cur_feature_pts, cur_descs, feature_points_plot = feature_extraction(cur_image, cur_image_gray, feature_points_plot)
    next_feature_pts, next_descs, feature_points_plot = feature_extraction(next_image, next_image_gray, feature_points_plot)

    # Feature matching
    matches = feature_matching(cur_image, cur_feature_pts, cur_descs, next_image, next_feature_pts, next_descs)

    # Find Homography matrix
    if len(matches[:, 0]) >= 4:
        match_pairs_list = []
        if matches is not None or matches is not []:
            for match in matches[:, 0]:
                (x1, y1) = next_feature_pts[match.queryIdx].pt
                (x2, y2) = cur_feature_pts[match.trainIdx].pt
                match_pairs_list.append([x1, y1, x2, y2])

        match_pairs_matrix = np.matrix(match_pairs_list)

        # Run RANSAC algorithm
        H, inliers = RANSAC(match_pairs_matrix, ransac_thresh)
        # src_pts = np.float32([next_feature_pts[m.queryIdx].pt for m in matches[:, 0]]).reshape(-1, 1, 2)
        # dst_pts = np.float32([cur_feature_pts[m.trainIdx].pt for m in matches[:, 0]]).reshape(-1, 1, 2)

        # H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
        print("Final homography: ", H)
        print("Final inliers count: ", len(inliers))

        # res = cv2.warpPerspective(next_image, H, (cur_image.shape[1], cur_image.shape[0]))
        # res[0:cur_image.shape[0], 0:cur_image.shape[1]] = cur_image
        # plt.imshow(res)
        # plt.title('Feature Points'), plt.xticks([]), plt.yticks([])
        # plt.show()

        # Merging by Transformation
        res = merge_images(cur_image, next_image, H)

    else:
        print("Can’t find enough keypoints.")
        res = next_image

    return res


def feature_extraction(img, img_gray, feature_points_plot):
    # Feature extraction: find the key points, compute the descriptors with ORB
    key_pts, descs = orb.detectAndCompute(img_gray, None)
    # Plots showing feature points for each ordered pair of sub-image
    drawn_key_pts = cv2.drawKeypoints(img, key_pts, None, color=(0, 255, 0), flags=0)

    if feature_points_plot is None:
        # Assign first image's feature points
        feature_points_plot = drawn_key_pts
    else:
        # Merge first and second images' feature points
        feature_points_plot = np.concatenate((feature_points_plot, drawn_key_pts), axis=1)
        # Plot feature points of images
        plt.imshow(cv2.cvtColor(feature_points_plot, cv2.COLOR_BGR2RGB))
        plt.title('Feature Points'), plt.xticks([]), plt.yticks([])
        plt.show()

    return key_pts, descs, feature_points_plot


def feature_matching(cur_image, cur_feature_pts, cur_descs, next_image, next_feature_pts, next_descs):

    # Matcher
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    index_params = dict(algorithm=6,
                        table_number=6,
                        key_size=12,
                        multi_probe_level=2)
    search_params = {}
    flann = cv2.FlannBasedMatcher(index_params, search_params)


    if (cur_descs is not None and len(cur_descs) > nearest_neighbor_num and
            next_descs is not None and len(next_descs) > nearest_neighbor_num):

        # Get knn detector
        matches = flann.knnMatch(next_descs, cur_descs, k=nearest_neighbor_num)

        # Apply ratio test
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:  # TODO
                good_matches.append([m])
        matches = np.asarray(good_matches)

        # cv2.drawMatchesKnn expects list of lists as matches.
        drawn_matches = cv2.drawMatchesKnn(cur_image, cur_feature_pts, next_image, next_feature_pts, good_matches, None, flags=2)    # TODO flag?
        plt.imshow(cv2.cvtColor(drawn_matches, cv2.COLOR_BGR2RGB))
        plt.title('Feature Point Matching Lines'), plt.xticks([]), plt.yticks([])
        plt.show()
        return matches

    else:
        # TODO
        plt.imshow(cv2.cvtColor(next_image, cv2.COLOR_BGR2RGB))
        plt.title('Feature Point Matching Lines'), plt.xticks([]), plt.yticks([])
        plt.show()
        return None


def RANSAC(match_pairs, thresh):

    max_inliers = []
    best_H = None

    for i in range(100):

        # Find 4 feature (random) points to calculate a homography
        corr1 = match_pairs[random.randrange(0, len(match_pairs))]
        corr2 = match_pairs[random.randrange(0, len(match_pairs))]
        randomFour = np.vstack((corr1, corr2))
        corr3 = match_pairs[random.randrange(0, len(match_pairs))]
        randomFour = np.vstack((randomFour, corr3))
        corr4 = match_pairs[random.randrange(0, len(match_pairs))]
        randomFour = np.vstack((randomFour, corr4))

        # Compute homography
        H = find_homography(randomFour)
        inliers = []

        # Compute inliers where ||pi’, H pi || <ε
        for i in range(len(match_pairs)):
            d = least_squares(match_pairs[i], H)
            if d < inlier_thresh:
                inliers.append(match_pairs[i])

        # Keep largest set of inliers
        if len(inliers) > len(max_inliers):
            max_inliers = inliers
            best_H = H

        print("Corr size: ", len(match_pairs), " NumInliers: ", len(inliers), "Max inliers: ", len(max_inliers))

        if len(max_inliers) > (len(match_pairs) * thresh):
            break

    return best_H, max_inliers


def find_homography(matches):
    # loop through correspondences and create assemble matrix
    aList = []
    for corr in matches:
        p1 = np.matrix([corr.item(0), corr.item(1), 1])
        p2 = np.matrix([corr.item(2), corr.item(3), 1])

        a2 = [0, 0, 0, -p2.item(2) * p1.item(0), -p2.item(2) * p1.item(1), -p2.item(2) * p1.item(2),
              p2.item(1) * p1.item(0), p2.item(1) * p1.item(1), p2.item(1) * p1.item(2)]

        a1 = [-p2.item(2) * p1.item(0), -p2.item(2) * p1.item(1), -p2.item(2) * p1.item(2), 0, 0, 0,
              p2.item(0) * p1.item(0), p2.item(0) * p1.item(1), p2.item(0) * p1.item(2)]

        aList.append(a1)
        aList.append(a2)

    matrixA = np.matrix(aList)

    # svd composition
    u, s, v = np.linalg.svd(matrixA)

    # reshape the min singular value into a 3 by 3 matrix
    H = np.reshape(v[8], (3, 3))

    # normalize and now we have h
    H = (1 / H.item(8)) * H
    return H


# Calculate the geometric distance between estimated points and original points
def least_squares(match_pairs, h):
    p1 = np.transpose(np.matrix([match_pairs[0].item(0), match_pairs[0].item(1), 1]))
    estimatep2 = np.dot(h, p1)
    estimatep2 = (1 / estimatep2.item(2)) * estimatep2

    p2 = np.transpose(np.matrix([match_pairs[0].item(2), match_pairs[0].item(3), 1]))
    error = p2 - estimatep2
    return np.linalg.norm(error)


def to_mtx(img):
    H, V, C = img.shape
    mtr = np.zeros((V, H, C), dtype='uint8')
    for i in range(img.shape[0]):
        mtr[:, i] = img[i]

    return mtr


def to_img(mtr):
    V, H, C = mtr.shape
    img = np.zeros((H, V, C), dtype='uint8')
    for i in range(mtr.shape[0]):
        img[:, i] = mtr[i]

    return img


def merge_images(cur_image, next_image, H):
    mtr = to_mtx(next_image)
    R, C = (cur_image.shape[1] + next_image.shape[1], cur_image.shape[0])
    dst = np.zeros((R, C, mtr.shape[2]))

    for i in range(mtr.shape[0]):
        for j in range(mtr.shape[1]):
            res = np.dot(H, [i, j, 1])
            i2 = int(res[0, 0] / res[0, 2] + 0.5)
            j2 = int(res[0, 1] / res[0, 2] + 0.5)
            if i2 >= 0 and i2 < R:
                if j2 >= 0 and j2 < C:
                    dst[i2, j2] = mtr[i, j]

    a = to_img(dst)
    plt.imshow(a)
    plt.title(''), plt.xticks([]), plt.yticks([])
    plt.show()

    a = cv2.medianBlur(a, 5)
    plt.imshow(a)
    plt.title(''), plt.xticks([]), plt.yticks([])
    plt.show()

    for i in range(cur_image.shape[0]):
        for j in range(cur_image.shape[1]):
            if cur_image[i, j][0] != 0 and cur_image[i, j][1] != 0 and cur_image[i, j][2] != 0:
                a[i, j] = cur_image[i, j]


    # a[0:cur_image.shape[0], 0:cur_image.shape[1]] = cur_image
    plt.imshow(a)
    plt.title(''), plt.xticks([]), plt.yticks([])
    plt.show()
    a = trim(a)
    plt.imshow(a)
    plt.title(''), plt.xticks([]), plt.yticks([])
    plt.show()
    return a


def crop_image(img):
    # Mask of non-black pixels (assuming image has a single channel).
    mask = img > 0

    # Coordinates of non-black pixels.
    coords = np.argwhere(mask)

    # Bounding box of non-black pixels.
    x0, y0, _ = coords.min(axis=0)
    x1, y1, _ = coords.max(axis=0) + 1  # slices are exclusive at the top

    # Get the contents of the bounding box.
    cropped = img[x0:x1, y0:y1]
    plt.imshow(cropped)
    plt.title(''), plt.xticks([]), plt.yticks([])
    plt.show()
    return cropped


def trim(frame):
    #crop top
    if not np.sum(frame[0]):
        return trim(frame[1:])
    #crop bottom
    elif not np.sum(frame[-1]):
        return trim(frame[:-2])
    #crop left
    elif not np.sum(frame[:,0]):
        return trim(frame[:,1:])
    #crop right
    elif not np.sum(frame[:,-1]):
        return trim(frame[:,:-2])

    return frame


if __name__ == '__main__':
    get_subset_names()
    main()
