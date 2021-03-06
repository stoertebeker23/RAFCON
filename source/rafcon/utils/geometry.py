# Copyright (C) 2015-2017 DLR
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Eclipse Public License v1.0 which
# accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
# Franz Steinmetz <franz.steinmetz@dlr.de>
# Sebastian Brunner <sebastian.brunner@dlr.de>

"""
.. module:: geometry
   :synopsis: A module holding all utility functions concerning geometric drawing

"""


from math import sqrt, pi


def dist(p1, p2):
    """Calculates the distance between two points

    The function calculates the Euclidean distance between the two 2D points p1 and p2
    :param p1: Tuple with x and y coordinate of the first point
    :param p2: Tuple with x and y coordinate of the second point
    :return: The Euclidean distance
    """
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def point_left_of_line(point, line_start, line_end):
    """Determines whether a point is left of a line

    :param point: Point to be checked (tuple with x any y coordinate)
    :param line_start: Starting point of the line (tuple with x any y coordinate)
    :param line_end: End point of the line (tuple with x any y coordinate)
    :return: True if point is left of line, else False
    """
    # determine sign of determinant
    # ((b.x - a.x)*(c.y - a.y) - (b.y - a.y)*(c.x - a.x)) > 0
    return ((line_end[0] - line_start[0]) * (point[1] - line_start[1]) -
            (line_end[1] - line_start[1]) * (point[0] - line_start[0])) < 0


def point_on_line(point, line_start, line_end, accuracy=50.):
    """Checks whether a point lies on a line

    The function checks whether the point "point" (P) lies on the line defined by its starting point line_start (A) and
    its end point line_end (B).
    This is done by comparing the distance of [AB] with the sum of the distances [AP] and [PB]. If the difference is
    smaller than [AB] / accuracy, the point P is assumed to be on the line. By increasing the value of accuracy (the
    default is 50), the tolerance is decreased.
    :param point: Point to be checked (tuple with x any y coordinate)
    :param line_start: Starting point of the line (tuple with x any y coordinate)
    :param line_end: End point of the line (tuple with x any y coordinate)
    :param accuracy: The higher this value, the less distance is tolerated
    :return: True if the point is one the line, False if not
    """
    length = dist(line_start, line_end)
    ds = length / float(accuracy)
    if -ds < (dist(line_start, point) + dist(point, line_end) - length) < ds:
        return True

    return False


def point_in_triangle(p, v1, v2, v3):
    """Checks whether a point is within the given triangle

    The function checks, whether the given point p is within the triangle defined by the the three corner point v1,
    v2 and v3.
    This is done by checking whether the point is on all three half-planes defined by the three edges of the triangle.
    :param p: The point to be checked (tuple with x any y coordinate)
    :param v1: First vertex of the triangle (tuple with x any y coordinate)
    :param v2: Second vertex of the triangle (tuple with x any y coordinate)
    :param v3: Third vertex of the triangle (tuple with x any y coordinate)
    :return: True if the point is within the triangle, False if not
    """
    def _test(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    b1 = _test(p, v1, v2) < 0.0
    b2 = _test(p, v2, v3) < 0.0
    b3 = _test(p, v3, v1) < 0.0

    return (b1 == b2) and (b2 == b3)


def deg2rad(degree):
    """Converts angle given in degrees into radian

    :param float degree: Angle to be converted
    :return: Angle in radian
    :rtype: float
    """
    return degree / 180. * pi


def rad2deg(radians):
    """Converts angle given in radian into degrees

    :param float radians: Angle to be converted
    :return: Angle in degree
    :rtype: float
    """
    return radians / pi * 180.
