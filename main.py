from manim import *
from manim.animation.animation import DEFAULT_ANIMATION_RUN_TIME
from manim.mobject.opengl_compatibility import ConvertToOpenGL

# from manim_presentation import Slide #as MyScene
from typing import Callable, Iterable, Optional, Sequence
from math import sin, cos, pi, sqrt
import numpy as np


# class MyScene(Slide):
#     def __init__(self, *args, **kwargs):
#         super(MyScene, self).__init__(*args, **kwargs)


class MyScene(Scene):
    def __init__(self, *args, **kwargs):
        super(MyScene, self).__init__(*args, **kwargs)

    def pause(self):
        self.wait(0.25)


def get_bounding_rect(mobject, buff=0, **kwargs):
    top = mobject.get_top()[1]
    bottom = mobject.get_bottom()[1]
    left = mobject.get_left()[0]
    right = mobject.get_right()[0]
    points = [
        [left - buff, top + buff, 1],
        [right + buff, top + buff, 1],
        [right + buff, bottom - buff, 1],
        [left - buff, bottom - buff, 1],
    ]
    return Polygon(*points, **kwargs)


class IndicateEdges(Transform):
    def __init__(
        self,
        mobject: "Mobject",
        scale_factor: float = 1.2,
        color: str = YELLOW,
        rate_func: Callable[[float, Optional[float]], np.ndarray] = there_and_back,
        **kwargs
    ) -> None:
        self.color = color
        self.scale_factor = scale_factor
        super().__init__(mobject, rate_func=rate_func, **kwargs)

    def create_target(self) -> "Mobject":
        target = self.mobject.copy()
        target.scale(self.scale_factor)
        target.set_stroke(self.color)
        return target


class Blink(Transform):
    def __init__(
        self,
        mobject: "Mobject",
        opacity=1,
        rate_func: Callable[[float, Optional[float]], np.ndarray] = there_and_back,
        **kwargs
    ) -> None:
        self.opacity = opacity
        super().__init__(mobject, rate_func=rate_func, **kwargs)

    def create_target(self) -> "Mobject":
        target = self.mobject.copy()
        target.set_opacity(self.opacity)
        return target


class Path(VMobject, metaclass=ConvertToOpenGL):
    def __init__(self, *points: Sequence[float], color=BLUE, **kwargs):
        super().__init__(color=color, **kwargs)

        first_vertex, *vertices = points

        self.start_new_path(np.array(first_vertex))
        self.add_points_as_corners(
            [np.array(vertex) for vertex in vertices],
        )


class Graph:
    def DefaultUnconnectedEdge(self, p1, p2, **kwargs):
        return DashedLine(
            p1,
            p2,
            stroke_width=10 * self.scale,
            dash_length=0.1 * self.scale,
            dashed_ratio=0.4,
            stroke_color=self.dashed_color,
            **kwargs,
        )

    def DefaultConnectedEdge(self, p1, p2, **kwargs):
        return Line(
            p1,
            p2,
            stroke_width=10 * self.scale,
            stroke_color=self.solid_color,
            **kwargs,
        )

    def __init__(
        self,
        points,
        scale=1,
        solid_color=WHITE,
        dashed_color=WHITE,
        connected_edge=None,
        unconnected_edge=None,
    ):
        self.points = {
            label: Dot(p, radius=0.15 * scale) for (label, p) in points.items()
        }
        self.edges = set()
        self.matching = set()
        self.lines = {}
        self.scale = scale
        self.solid_color = solid_color
        self.dashed_color = dashed_color
        self.connected_edge = connected_edge or self.DefaultConnectedEdge
        self.unconnected_edge = unconnected_edge or self.DefaultUnconnectedEdge

    def get_group(self):
        return VGroup(
            *self.lines.values(),
            *self.points.values(),
        )

    def get_sub_group(self, vertices):
        points = [self.points[v] for v in vertices]
        edges = [
            self.lines[e] for e in self.edges if e[0] in vertices and e[1] in vertices
        ]
        return Group(*edges, *points)

    def draw_points(self, scene):
        scene.add(*self.points.values())

    def apply_to_all(self, animation, **kwargs):
        return AnimationGroup(
            *[animation(l) for l in self.lines.values()],
            *[animation(p) for p in self.points.values()],
            **kwargs,
        )

    def shift(self, delta, animate=True):
        if animate:
            return AnimationGroup(
                *[
                    p.animate.move_to(p.get_center() + delta)
                    for p in self.points.values()
                ],
                *[
                    l.animate.put_start_and_end_on(
                        l.get_start() + delta, l.get_end() + delta
                    )
                    for l in self.lines.values()
                ],
            )

        for p in self.points.values():
            p.move_to(p.get_center() + delta)
        for l in self.lines.values():
            l.put_start_and_end_on(l.get_start() + delta, l.get_end() + delta)

    def add_edge(self, p1, p2):
        edge = tuple(sorted((p1, p2)))
        self.edges.add(edge)
        line = self._make_edge(edge)
        self.lines[edge] = line

    def add_point(self, label, p, hidden=False):
        self.points[label] = Dot(
            p, radius=0 if hidden else 0.15 * self.scale, z_index=100
        )

    def _make_edge(self, edge):
        p1 = self.points[edge[0]].get_center()
        p2 = self.points[edge[1]].get_center()
        if edge in self.matching:
            return self.connected_edge(p1, p2, buff=0.15 * self.scale)
        else:
            return self.unconnected_edge(p1, p2, buff=0.15 * self.scale)

    def make_edges(self):
        pass

    def draw_edges(self, scene):
        if not self.lines:
            self.make_edges()
        for edge in self.edges:
            scene.add(self.lines[edge])

    def match(self, p1, p2):
        self.matching.add(tuple(sorted((p1, p2))))

    def unmatch(self, p1, p2):
        self.matching.remove(tuple(sorted((p1, p2))))

    def update_matching(self, animated=True, fade=False):
        animations = []
        for edge in self.edges:
            old_line = self.lines[edge]
            new_line = self._make_edge(edge)
            if old_line.__class__.__name__ != new_line.__class__.__name__:
                self.lines[edge] = new_line
                if animated:
                    if fade:
                        animations.append(FadeOut(old_line))
                        animations.append(FadeIn(new_line))
                    else:
                        if isinstance(new_line, DashedLine):
                            animations.append(
                                AnimationGroup(
                                    FadeIn(new_line, time=0),
                                    ShrinkToCenter(old_line),
                                )
                            )
                        else:
                            animations.append(
                                AnimationGroup(
                                    GrowFromCenter(new_line),
                                    FadeOut(old_line, time=0),
                                )
                            )

        return animations if animated else None

    def rearrange(self, new_points, dont_stretch={}, animated=True):
        dont_stretch = set(tuple(sorted(x)) for x in dont_stretch)
        edges = [
            edge
            for edge in self.edges
            if edge[0] in new_points or edge[1] in new_points
        ]
        new_line_start_ends = [
            (
                new_points.get(edge[0], self.lines[edge].get_start()),
                new_points.get(edge[1], self.lines[edge].get_end()),
                edge,
            )
            for edge in edges
        ]
        if not animated:
            for (start, end, edge) in new_line_start_ends:
                self.lines[edge].put_start_and_end_on(start, end)
            for key, new_point in new_points.items():
                self.points[key].move_to(new_point)

        return AnimationGroup(
            *[
                self.points[key].animate.move_to(new_point)
                for key, new_point in new_points.items()
            ],
            *[
                Transform(
                    self.lines[edge],
                    (
                        self.connected_edge
                        if edge in self.matching
                        else self.unconnected_edge
                    )(start, end),
                )
                if edge in dont_stretch
                else self.lines[edge].animate.put_start_and_end_on(start, end)
                for (start, end, edge) in new_line_start_ends
            ],
        )

    def highlight_path(self, *points):
        line_points = [self.points[x].get_center() for x in points]
        line = (
            Path(*line_points)
            .set_stroke(color=YELLOW, width=30, opacity=0.5)
            .set_z_index(-1)
        )
        return line

    def invert_path(self, *points):
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            edge = (p1, p2)
            if edge in self.matching:
                self.unmatch(*edge)
            else:
                self.match(*edge)


def _make_even_cycle_graph():
    graph = Graph(
        {
            "A": [-2, 1, 0],
            "B": [-2, -1, 0],
            "C": [0, -1, 0],
            "D": [0, 1, 0],
            "E": [2, 1, 0],
            "F": [2, -1, 0],
        }
    )

    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "D")
    graph.add_edge("D", "E")
    graph.add_edge("E", "F")
    graph.add_edge("F", "C")
    return graph


def make_matte(w, h):
    bg = (
        Rectangle(width=10, height=10)
        .set_fill(color=BLACK, opacity=0.5)
        .set_stroke(width=0)
    )
    bg2 = (
        Rectangle(width=w, height=h)
        .set_fill(color=BLACK, opacity=1)
        .set_stroke(width=0)
    )
    outline = Rectangle(width=w, height=h).set_stroke(color=WHITE)
    return (
        AnimationGroup(FadeIn(bg), FadeIn(bg2), Create(outline)),
        AnimationGroup(FadeOut(bg), FadeOut(bg2), FadeOut(outline)),
    )


class StableMatching(MyScene):
    def construct(self):
        text = [
            [
                MathTex("A", font_size=64),
                MathTex("B", font_size=64),
                MathTex("C", font_size=64),
            ],
            [
                MathTex(r"\alpha", font_size=64),
                MathTex(r"\beta", font_size=64),
                MathTex(r"\gamma", font_size=64),
            ],
        ]

        grid = VGroup(*text[0], *text[1]).arrange_in_grid(
            cols=2, flow_order="dr", col_widths=[3] * 2, row_heights=[2] * 3
        )

        self.play(FadeIn(grid))
        self.pause()
        self.play(Circumscribe(VGroup(*text[0]), time_width=0.5, buff=0.2))
        self.pause()
        self.play(Circumscribe(VGroup(*text[1]), time_width=0.5, buff=0.2))
        self.pause()

        def edge(a, b):
            return Arrow(
                text[a[0]][a[1]].get_center(), text[b[0]][b[1]].get_center(), buff=0.5
            )

        matching1 = [
            edge((0, 0), (1, 1)),
            edge((0, 1), (1, 2)),
            edge((0, 2), (1, 0)),
        ]

        self.play(LaggedStart(*[GrowArrow(a) for a in matching1], lag_ratio=0.25))
        self.pause()
        self.play(LaggedStart(*[FadeOut(a) for a in matching1], lag_ratio=0.15))
        self.pause()

        matching2 = [
            edge((0, 0), (1, 0)),
            edge((0, 1), (1, 1)),
            edge((0, 2), (1, 2)),
        ]

        self.play(LaggedStart(*[GrowArrow(a) for a in matching2], lag_ratio=0.25))
        self.pause()
        self.play(LaggedStart(*[FadeOut(a) for a in matching2], lag_ratio=0.15))
        self.pause()

        show, hide = make_matte(8, 2)
        popup_text = Group(
            Text("1. Evaluate potential pairings", font_size=32),
            Text("2. Find optimal matching", font_size=32),
        ).arrange(DOWN, aligned_edge=LEFT)

        self.play(LaggedStart(show, Write(popup_text[0]), lag_ratio=0.2))
        self.pause()
        self.play(Write(popup_text[1]))
        self.pause()

        self.play(
            LaggedStart(
                FadeOut(popup_text[0]),
                popup_text[1].animate.move_to(
                    [popup_text[1].get_center()[0], popup_text[0].get_center()[1], 0]
                ),
            )
        )
        self.pause()

        popup_text_2 = Group(
            Text(
                "Stable\nmatching", should_center=True, font_size=36, line_spacing=0.5
            ),
            Line([0, -0.5, 0], [0, 0.5, 0]),
            Text(
                "Maximum\nmatching", should_center=True, font_size=36, line_spacing=0.5
            ),
        ).arrange(RIGHT, buff=0.8)

        self.play(
            LaggedStart(FadeOut(popup_text[1]), FadeIn(popup_text_2), lag_ratio=0.4)
        )
        self.pause()
        self.play(Indicate(popup_text_2[0]))
        self.pause()

        self.play(AnimationGroup(hide, FadeOut(popup_text_2)))
        self.pause()

        pref_squares = [
            VGroup(*[Square(0.26) for _ in range(3)])
            .set_stroke(width=2)
            .set_fill(color=BLACK, opacity=1)
            .arrange(DOWN, buff=0)
            .next_to(letter, direction=LEFT if i == 0 else RIGHT)
            .set_z_index(-1)
            for i, column in enumerate(text)
            for letter in column
        ]

        prefs = [
            [r"\alpha", r"\beta", r"\gamma"],
            [r"\beta", r"\alpha", r"\gamma"],
            [r"\alpha", r"\gamma", r"\beta"],
            ["B", "A", "C"],
            ["A", "B", "C"],
            ["C", "A", "B"],
        ]

        prefs_mtext = [
            [
                MathTex(s, font_size=24).move_to(pref_squares[i][j])
                for j, s in enumerate(pref)
            ]
            for i, pref in enumerate(prefs)
        ]

        self.play(
            LaggedStart(*[Create(prefs) for prefs in pref_squares[0]], lag_ratio=0.2)
        )
        self.play(LaggedStart(*[Write(x) for x in prefs_mtext[0]], lag_ratio=0.4))
        self.pause()

        self.play(
            LaggedStart(
                *[Create(prefs) for prefs in pref_squares[1:3]],
                *[Write(x) for pref_group in prefs_mtext[1:3] for x in pref_group],
                lag_ratio=0.3,
            )
        )
        self.pause()

        self.play(
            LaggedStart(
                *[Create(prefs) for prefs in pref_squares[3:]],
                *[Write(x) for pref_group in prefs_mtext[3:] for x in pref_group],
                lag_ratio=0.3,
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[0][0]),
                IndicateEdges(pref_squares[0][0], scale_factor=1.5),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[3][1]),
                IndicateEdges(pref_squares[3][1], scale_factor=1.5),
            )
        )
        self.pause()

        # matte_stack = [
        #     Rectangle(width=10,  height=10).set_fill(color=BLACK, opacity=0.5).set_stroke(width=0),
        #     Rectangle(width=6, height=2).set_fill(color=BLACK, opacity=1).set_stroke(color=WHITE)
        # ]
        # stable_matching_text = Text("Stable Matching", slant=ITALIC).move_to([0,0,0])
        # self.play(LaggedStart(
        #     FadeIn(VGroup(*matte_stack)),
        #     Write(stable_matching_text)
        # ))
        # self.pause()

        # self.play(AnimationGroup(
        #     FadeOut(VGroup(*matte_stack)),
        #     FadeOut(stable_matching_text),
        # ))
        # self.pause()

        self.play(LaggedStart(*[GrowArrow(a) for a in matching1], lag_ratio=0.25))
        self.pause()

        self.play(
            LaggedStart(Indicate(text[0][0]), Indicate(text[1][0]), lag_ratio=0.8)
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[0][1]),
                Indicate(prefs_mtext[3][2]),
                IndicateEdges(pref_squares[0][1], scale_factor=1.5),
                IndicateEdges(pref_squares[3][2], scale_factor=1.5),
                Indicate(matching1[0]),
                Indicate(matching1[2]),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[0][0]),
                Indicate(prefs_mtext[3][1]),
                IndicateEdges(pref_squares[0][0], scale_factor=1.5),
                IndicateEdges(pref_squares[3][1], scale_factor=1.5),
            )
        )
        self.pause()

        matching1[0].set_z_index(-1)
        matching1[2].set_z_index(-1)
        self.play(
            AnimationGroup(
                matching1[0].animate.set_stroke(color=GRAY_E).set_fill(color=GRAY_E),
                matching1[2].animate.set_stroke(color=GRAY_E).set_fill(color=GRAY_E),
            )
        )
        self.pause()

        self.play(
            Circumscribe(
                VGroup(text[0][0], text[1][0], *prefs_mtext[0], *prefs_mtext[3])
            )
        )
        self.pause()

        extra_edge = edge((0, 0), (1, 0))
        self.play(GrowArrow(extra_edge))
        self.pause()

        self.play(AnimationGroup(Indicate(text[0][2]), Indicate(text[1][1])))
        self.pause()

        self.play(AnimationGroup(*[FadeOut(a) for a in matching1], FadeOut(extra_edge)))
        self.pause()

        matching3 = [
            edge((0, 0), (1, 1)),
            edge((0, 1), (1, 0)),
            edge((0, 2), (1, 2)),
        ]
        self.play(LaggedStart(*[GrowArrow(a) for a in matching3], lag_ratio=0.25))
        self.pause()

        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[0][1]),
                IndicateEdges(pref_squares[0][1], scale_factor=1.5),
                Indicate(matching3[0]),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[0][0]),
                IndicateEdges(pref_squares[0][0], scale_factor=1.5),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(prefs_mtext[3][0]),
                IndicateEdges(pref_squares[3][0], scale_factor=1.5),
                Indicate(matching3[1]),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                *(FadeOut(x) for y in prefs_mtext for x in y),
                *(FadeOut(x) for x in pref_squares),
                *(FadeOut(x) for x in matching3),
            )
        )
        self.pause()


class StableVsMaximumTable(MyScene):
    def construct(self):
        stable = Tex("Stable Matching", font_size=64).move_to([-3.5, 0, 0])
        maximum = Tex("Maximum Matching", font_size=64).move_to([3.5, 0, 0])
        vline = Line([0, 0.6, 0], [0, -5.5, 0])
        titles = VGroup(stable, vline, maximum).to_edge(UP, buff=1)
        hline = Line([-7.5, 0, 0], [7.5, 0, 0])
        hline.align_to(maximum.get_critical_point(DOWN) + DOWN * 0.3, DOWN)

        def bullet(str):
            return Tex(
                r"""
            \begin{itemize}
              \item """
                + str
                + r"""
            \end{itemize}
            """
            )

        list_left = (
            VGroup(
                bullet(r"Anyone can be matched\\with anyone"),
                bullet(r"Everyone will be matched"),
                bullet(r"Preference ranking"),
                bullet(r"Maximize stability"),
            )
            .arrange(DOWN, aligned_edge=LEFT, buff=0.5)
            .align_to([-6.7, 0, 0], LEFT)
            .align_to(hline.get_center() + DOWN * 0.6, UP)
        )

        list_right = (
            VGroup(
                bullet(r"Not everyone can be\\matched"),
                bullet(r"Maximize number of\\individuals matched"),
            )
            .arrange(DOWN, aligned_edge=LEFT, buff=0.5)
            .align_to([0.5, 0, 0], LEFT)
            .align_to(hline.get_center() + DOWN * 0.6, UP)
        )

        self.play(
            LaggedStart(Create(hline), Create(vline), Write(stable), lag_ratio=0.2)
        )

        self.pause()
        for l in list_left:
            self.play(Write(l))
            self.pause()
        self.play(Write(maximum))
        self.pause()
        for l in list_right:
            self.play(Write(l))
            self.pause()

        self.add(titles)
        self.add(hline)
        self.add(list_left)
        self.add(list_right)


class MaximumMatchingIntro(MyScene):
    def construct(self):
        text = [
            [
                MathTex("A", font_size=64),
                MathTex("B", font_size=64),
                MathTex("C", font_size=64),
            ],
            [
                MathTex(r"\alpha", font_size=64),
                MathTex(r"\beta", font_size=64),
                MathTex(r"\gamma", font_size=64),
            ],
        ]

        grid = VGroup(*text[0], *text[1]).arrange_in_grid(
            cols=2, flow_order="dr", col_widths=[3] * 2, row_heights=[2] * 3
        )
        self.add(grid)
        self.pause()

        p_a = text[0][0].get_center()
        p_b = text[0][1].get_center()
        p_c = text[0][2].get_center()
        p_1 = text[1][0].get_center()
        p_2 = text[1][1].get_center()
        p_3 = text[1][2].get_center()

        def dashed_line(p1, p2):
            return DashedLine(
                p1,
                p2,
                stroke_width=10,
                dash_length=0.1,
                dashed_ratio=0.4,
                buff=0.5,
                stroke_color=GRAY_D,
            )

        def solid_line(p1, p2):
            return Line(p1, p2, stroke_width=10, buff=0.5, z_index=10)

        edges = [
            dashed_line(p_a, p_1),
            dashed_line(p_a, p_2),
            dashed_line(p_b, p_2),
            dashed_line(p_b, p_3),
            dashed_line(p_c, p_2),
        ]
        self.play(AnimationGroup(*(FadeIn(e) for e in edges)))
        self.pause()

        l1 = solid_line(p_a, p_1)
        l2 = solid_line(p_b, p_2)
        self.play(
            AnimationGroup(
                GrowFromCenter(l1),
                FadeOut(edges[0]),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                GrowFromCenter(l2),
                FadeOut(edges[2]),
            )
        )
        self.pause()

        self.play(Indicate(text[0][2]))
        self.pause()

        self.play(
            AnimationGroup(
                ShrinkToCenter(l1),
                ShrinkToCenter(l2),
                FadeIn(edges[0]),
                FadeIn(edges[2]),
            )
        )
        self.pause()

        l1 = solid_line(p_a, p_1)
        l3 = solid_line(p_b, p_3)
        l4 = solid_line(p_c, p_2)
        self.play(
            LaggedStart(
                AnimationGroup(
                    GrowFromCenter(l1),
                    FadeOut(edges[0]),
                ),
                AnimationGroup(
                    GrowFromCenter(l3),
                    FadeOut(edges[3]),
                ),
                AnimationGroup(
                    GrowFromCenter(l4),
                    FadeOut(edges[4]),
                ),
                lag_ratio=0.25,
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                ShrinkToCenter(l1),
                ShrinkToCenter(l3),
                ShrinkToCenter(l4),
                FadeIn(edges[0]),
                FadeIn(edges[3]),
                FadeIn(edges[4]),
            )
        )
        self.pause()

        p_a += LEFT
        p_b += LEFT
        p_c += LEFT
        p_1 += RIGHT
        p_2 += RIGHT
        p_3 += RIGHT

        self.play(
            AnimationGroup(
                *[t.animate.shift(LEFT) for t in text[0]],
                *[t.animate.shift(RIGHT) for t in text[1]],
                # *[e.animate.put_start_and_end_on(e.get_start() + LEFT, e.get_end() + RIGHT) for e in edges]
                # *[Transform(e, dashed_line(e.get_start() + LEFT, e.get_end() + RIGHT)) for e in edges]
                Transform(edges[0], dashed_line(p_a, p_1)),
                Transform(edges[1], dashed_line(p_a, p_2)),
                Transform(edges[2], dashed_line(p_b, p_2)),
                Transform(edges[3], dashed_line(p_b, p_3)),
                Transform(edges[4], dashed_line(p_c, p_2)),
            )
        )
        self.pause()

        arrows = [Arrow(e.get_start(), e.get_end(), buff=0) for e in edges]
        self.play(
            LaggedStart(
                *[
                    AnimationGroup(
                        FadeOut(edges[i]),
                        GrowArrow(arrows[i]),
                    )
                    for i in range(len(edges))
                ],
                lag_ratio=0.2,
            )
        )

        capacities = [
            MathTex("0", "/", "1", font_size=36).next_to(
                edges[0].get_center(), direction=UP
            ),
            MathTex("0", "/", "1", font_size=36).next_to(
                edges[1].get_end() + 0.25 * UP, direction=UP + LEFT, buff=0.5
            ),
            MathTex("0", "/", "1", font_size=36).next_to(
                edges[2].get_center(), direction=UP
            ),
            MathTex("0", "/", "1", font_size=36).next_to(
                edges[4].get_end() + 0.25 * DOWN, direction=DOWN + LEFT, buff=0.5
            ),
            MathTex("0", "/", "1", font_size=36).next_to(
                edges[3].get_end(), direction=LEFT, buff=1
            ),
        ]

        self.play(LaggedStart(*[Write(x) for x in capacities], lag_ratio=0.15))
        self.pause()

        def set_fill(capacities, i, s):
            return Transform(
                capacities[i][0], MathTex(s, font_size=36).move_to(capacities[i][0])
            )

        self.play(set_fill(capacities, 0, "1"))
        self.pause()
        self.play(set_fill(capacities, 0, "0"))
        self.pause()

        source = MathTex("s", font_size=64).next_to(p_b, direction=LEFT, buff=3)
        sink = MathTex("t", font_size=64).next_to(p_2, direction=RIGHT, buff=3)
        p_s = source.get_center()
        p_t = sink.get_center()

        st_arrows = [
            Arrow(p_s, p_a, buff=0.5),
            Arrow(p_s, p_b, buff=0.5),
            Arrow(p_s, p_c, buff=0.5),
            Arrow(p_1, p_t, buff=0.5),
            Arrow(p_2, p_t, buff=0.5),
            Arrow(p_3, p_t, buff=0.5),
        ]

        st_capacities = [
            MathTex("0", "/", "1", font_size=36).next_to(
                arrow.get_center(), direction=UP
            )
            for arrow in st_arrows
        ]

        self.play(
            LaggedStart(
                Write(source),
                *[GrowArrow(x) for x in st_arrows[:3]],
                *[Write(x) for x in st_capacities[:3]],
                lag_ratio=0.15,
            )
        )
        self.pause()

        self.play(
            LaggedStart(
                Write(sink),
                *[GrowArrow(x) for x in st_arrows[3:]],
                *[Write(x) for x in st_capacities[3:]],
                lag_ratio=0.15,
            )
        )
        self.pause()

        for obj in arrows + st_arrows + text[0] + text[1] + [source, sink]:
            obj.set_z_index(10)

        flow1 = Path(p_s, p_a, p_1, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow1, run_time=1.6),
                set_fill(st_capacities, 0, "1"),
                set_fill(capacities, 0, "1"),
                set_fill(st_capacities, 3, "1"),
                lag_ratio=0.15,
            )
        )
        self.pause()

        flow2 = Path(p_s, p_b, p_3, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow2, run_time=1.6),
                set_fill(st_capacities, 1, "1"),
                set_fill(capacities, 4, "1"),
                set_fill(st_capacities, 5, "1"),
                lag_ratio=0.15,
            )
        )
        self.pause()

        flow3 = Path(p_s, p_c, p_2, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow3, run_time=1.6),
                set_fill(st_capacities, 2, "1"),
                set_fill(capacities, 3, "1"),
                set_fill(st_capacities, 4, "1"),
                lag_ratio=0.15,
            )
        )
        self.pause()

        st_group = VGroup(*st_capacities, *st_arrows, source, sink)

        self.play(st_group.animate.set_stroke(opacity=0.25).set_fill(opacity=0.25))
        self.pause()

        self.play(Indicate(VGroup(arrows[0], arrows[3], arrows[4])))
        self.pause()

        self.play(st_group.animate.set_stroke(opacity=1).set_fill(opacity=1))
        self.pause()

        self.play(Circumscribe(VGroup(VGroup(*st_capacities[:3])), buff=0.2))
        self.pause()
        self.play(Circumscribe(VGroup(VGroup(*text[0])), buff=0.2))
        self.pause()
        self.play(Circumscribe(VGroup(VGroup(*st_capacities[3:])), buff=0.2))
        self.pause()
        self.play(Circumscribe(VGroup(VGroup(*text[1])), buff=0.2))
        self.pause()

        flow_direction = Arrow(p_a + UP, p_1 + UP, color=YELLOW)
        self.play(GrowArrow(flow_direction))
        self.pause()
        self.play(FadeOut(flow_direction))
        self.pause()

        self.play(Circumscribe(VGroup(VGroup(*text[1])), buff=0.2))
        self.pause()
        self.play(LaggedStart(*(Indicate(a) for a in st_arrows[3:]), lag_ratio=0.15))
        self.pause()
        flow_direction = (
            Arrow(
                [00, 0, 0],
                [1, 0, 0],
                color=YELLOW,
            )
            .set_stroke(width=8)
            .next_to(sink, DOWN, buff=0.3)
        )
        self.play(GrowArrow(flow_direction))
        self.pause()
        self.play(FadeOut(flow_direction))
        self.pause()

        self.play(
            AnimationGroup(
                *[set_fill(capacities, i, 0) for i in range(len(capacities))],
                *[set_fill(st_capacities, i, 0) for i in range(len(st_capacities))],
                FadeOut(flow1),
                FadeOut(flow2),
                FadeOut(flow3),
            )
        )
        self.pause()

        def set_cap(capacities, i, s):
            return Transform(
                capacities[i][2], MathTex(s, font_size=36).move_to(capacities[i][2])
            )

        self.play(
            AnimationGroup(*[set_cap(st_capacities, i, "2") for i in range(3, 6)])
        )
        self.pause()

        flow1 = Path(p_s, p_a, p_2, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow1, run_time=1.6),
                set_fill(st_capacities, 0, "1"),
                set_fill(capacities, 1, "1"),
                set_fill(st_capacities, 4, "1"),
                lag_ratio=0.15,
            )
        )
        self.pause()
        flow2 = Path(p_s, p_c, p_2, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow2, run_time=1.6),
                set_fill(st_capacities, 2, "1"),
                set_fill(capacities, 3, "1"),
                set_fill(st_capacities, 4, "2"),
                lag_ratio=0.15,
            )
        )
        self.pause()
        # flow3 = Path(p_s, p_b, p_3, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        # self.play(LaggedStart(
        #     Create(flow3, run_time=1.6),
        #     set_fill(st_capacities, 1, "1"),
        #     set_fill(capacities, 4, "1"),
        #     set_fill(st_capacities, 5, "1"),
        #     lag_ratio=0.15
        # ))
        # self.pause()

        self.play(
            AnimationGroup(
                *[set_fill(capacities, i, 0) for i in range(len(capacities))],
                *[set_fill(st_capacities, i, 0) for i in range(len(st_capacities))],
                *[set_cap(st_capacities, i, 1) for i in range(len(st_capacities))],
                FadeOut(flow1),
                FadeOut(flow2),
                # FadeOut(flow3),
            )
        )
        self.pause()

        self.play(AnimationGroup(*[set_cap(st_capacities, i, "2") for i in range(3)]))
        self.pause()

        flow1 = Path(p_s, p_b, p_2, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow1, run_time=1.6),
                set_fill(st_capacities, 1, "1"),
                set_fill(capacities, 2, "1"),
                set_fill(st_capacities, 4, "1"),
                lag_ratio=0.15,
            )
        )
        self.pause()
        flow2 = Path(p_s, p_b, p_3, p_t).set_stroke(color=BLUE, opacity=0.5, width=20)
        self.play(
            LaggedStart(
                Create(flow2, run_time=1.6),
                set_fill(st_capacities, 1, "2"),
                set_fill(capacities, 3, "1"),
                set_fill(st_capacities, 5, "1"),
                lag_ratio=0.15,
            )
        )
        self.pause()
        # self.play(AnimationGroup(
        #     *[set_cap(st_capacities, i, "1") for i in range(3)],
        #     *[set_fill(capacities, i, 0) for i in range(len(capacities))],
        #     *[set_fill(st_capacities, i, 0) for i in range(len(st_capacities))],
        #     FadeOut(flow1),
        #     FadeOut(flow2),
        # ))
        # self.pause()
        everything = VGroup(
            *arrows, *st_arrows, *capacities, *st_capacities, grid, source, sink
        )
        self.play(
            AnimationGroup(
                FadeOut(everything),
                FadeOut(flow1),
                FadeOut(flow2),
            )
        )
        self.pause()


class FourProblems(MyScene):
    def construct(self):
        graph_scale = 0.6

        def scale_map(map, scalar):
            return {k: [scalar * x for x in v] for k, v in map.items()}

        def solid_line(p1, p2, **kwargs):
            return Line(
                p1, p2, stroke_width=8 * graph_scale, stroke_color=WHITE, **kwargs
            )

        def make_general_graph():
            g = Graph(
                scale_map(
                    {
                        "A": [0, 1, 0],
                        "B": [sin(2 * pi / 5), cos(2 * pi / 5), 0],
                        "C": [sin(4 * pi / 5), -cos(pi / 5), 0],
                        "D": [-sin(4 * pi / 5), -cos(pi / 5), 0],
                        "E": [-sin(2 * pi / 5), cos(2 * pi / 5), 0],
                        "F": [0, 0, 0],
                    },
                    graph_scale,
                ),
                scale=graph_scale,
                unconnected_edge=solid_line,
            )

            vertices = ["A", "B", "C", "D", "E"]
            for i in range(5):
                g.add_edge(vertices[i], vertices[(i + 1) % 5])
                g.match(vertices[i], vertices[(i + 1) % 5])
                g.add_edge(vertices[i], "F")
                g.match(vertices[i], "F")

            return g

        def make_bipartite_graph():
            g = Graph(
                scale_map(
                    {
                        "A": [0, 0, 0],
                        "B": [0, 1, 0],
                        "C": [0, 2, 0],
                        "D": [1.5, 0, 0],
                        "E": [1.5, 1, 0],
                        "F": [1.5, 2, 0],
                    },
                    graph_scale,
                ),
                scale=graph_scale,
                unconnected_edge=solid_line,
            )

            for a in ["A", "B", "C"]:
                for b in ["D", "E", "F"]:
                    g.add_edge(a, b)
                    g.match(a, b)

            return g

        grid_size = 2.5

        general = make_general_graph()
        general.make_edges()
        general_group = general.get_group().move_to([grid_size * 2, 0, 0])

        bipartite = make_bipartite_graph()
        bipartite.make_edges()
        bipartite_group = bipartite.get_group().move_to([grid_size, 0, 0])

        weighted = Tex("Weighted").move_to([-0.15, -grid_size * 2, 0])
        unweighted = (
            Tex("Unweighted").move_to([0, -grid_size, 0]).align_to(weighted, RIGHT)
        )

        lines = [
            Line(
                [0.5 * grid_size, 0.5 * grid_size, 0],
                [0.5 * grid_size, -2.5 * grid_size, 0],
                stroke_width=6,
            ),
            Line(
                [1.5 * grid_size, 0.5 * grid_size, 0],
                [1.5 * grid_size, -2.5 * grid_size, 0],
                stroke_width=3,
            ),
            Line(
                [-0.5 * grid_size, -0.5 * grid_size, 0],
                [2.5 * grid_size, -0.5 * grid_size, 0],
                stroke_width=6,
            ),
            Line(
                [-0.5 * grid_size, -1.5 * grid_size, 0],
                [2.5 * grid_size, -1.5 * grid_size, 0],
                stroke_width=3,
            ),
        ]
        numbers = [
            MathTex("1", font_size=72).move_to([grid_size, -grid_size, 0]),
            MathTex("2", font_size=72).move_to([2 * grid_size, -grid_size, 0]),
            MathTex("3", font_size=72).move_to([grid_size, -2 * grid_size, 0]),
            MathTex("4", font_size=72).move_to([2 * grid_size, -2 * grid_size, 0]),
        ]
        cursor = Square(grid_size - 0.1, stroke_color=YELLOW, stroke_width=10).move_to(
            [grid_size, -grid_size, 0]
        )
        complexity = [
            MathTex(r"O(mn^2)", font_size=36).move_to([grid_size, -grid_size, 0]),
            MathTex(r"O(mn^2)", font_size=36).move_to([2 * grid_size, -grid_size, 0]),
            MathTex(r"O(n^2)", font_size=36).move_to([grid_size, -2 * grid_size, 0]),
            MathTex(r"O(n^3)", font_size=36).move_to(
                [2 * grid_size, -2 * grid_size, 0]
            ),
        ]
        all = Group(
            general.get_group(),
            bipartite.get_group(),
            unweighted,
            weighted,
            *lines,
            cursor,
            *numbers,
            *complexity,
        ).move_to(ORIGIN)

        self.play(LaggedStart(*[Create(x) for x in lines], lag_ratio=0.2))
        self.pause()
        self.play(
            bipartite.apply_to_all(lambda x: Create(x, run_time=0.5), lag_ratio=0.1)
        )
        self.pause()
        self.play(
            general.apply_to_all(lambda x: Create(x, run_time=0.5), lag_ratio=0.1)
        )
        self.pause()
        self.play(Circumscribe(bipartite.get_sub_group(["A", "B", "C"])))
        self.pause()
        self.play(Circumscribe(bipartite.get_sub_group(["D", "E", "F"])))
        self.pause()
        self.play(Circumscribe(general.get_group(), Circle))
        self.pause()
        self.play(bipartite.get_group().animate.shift(0.25 * UP))
        self.pause()
        self.play(
            Write(Tex(r"Bipartite", font_size=28).next_to(bipartite.get_group(), DOWN))
        )
        self.pause()
        self.play(general.get_group().animate.shift(0.25 * UP))
        self.pause()
        self.play(
            Write(Tex(r"General", font_size=28).next_to(general.get_group(), DOWN))
        )
        self.pause()
        self.play(Write(unweighted))
        self.pause()
        self.play(unweighted.animate.shift(0.35 * UP))
        self.pause()
        self.play(
            Write(
                Tex(r"(Maximum cardinality)", font_size=28).next_to(
                    unweighted, DOWN, aligned_edge=RIGHT
                )
            )
        )
        self.pause()
        self.play(Write(weighted))
        self.pause()
        self.play(weighted.animate.shift(0.35 * UP))
        self.pause()
        self.play(
            Write(
                Tex(r"(Maximum weight)", font_size=28).next_to(
                    weighted, DOWN, aligned_edge=RIGHT
                )
            )
        )
        self.pause()

        self.play(LaggedStart(*[Write(x) for x in numbers], lag_ratio=0.4))

        self.play(Create(cursor))
        self.pause()

        self.play(cursor.animate.shift(RIGHT * grid_size))
        self.pause()

        self.play(FadeOut(cursor), *[FadeOut(x) for x in numbers])
        self.pause()

        self.play(Write(complexity[0]))
        self.pause()
        self.play(
            Transform(
                complexity[0],
                MathTex(r"O(m\sqrt{n})", font_size=36).move_to(complexity[0]),
            )
        )
        self.pause()

        self.play(Write(complexity[1]))
        self.pause()
        self.play(
            Transform(
                complexity[1],
                MathTex(r"O(m\sqrt{n})", font_size=36).move_to(complexity[1]),
            )
        )
        self.pause()

        complexity_3_original = complexity[3].copy()

        self.play(Write(complexity[2]))
        self.pause()
        self.play(Write(complexity[3]))
        self.pause()
        self.play(
            Transform(
                complexity[3],
                MathTex(r"O(nm+n^2\log{n})", font_size=36).move_to(
                    complexity[3], aligned_edge=LEFT
                ),
            )
        )
        self.pause()
        self.play(Transform(complexity[3], complexity_3_original))
        self.pause()


class AugmentingPath(MyScene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.draw_points(self)
        graph.draw_edges(self)
        self.pause()

        vert = Tex("Vertices", color=RED)
        edges = Tex("Edges", color=GREEN)
        VGroup(vert, edges).arrange(DOWN, aligned_edge=LEFT).next_to(
            graph.get_group(), RIGHT, buff=0.5
        )

        self.play(
            Indicate(
                VGroup(*graph.points.values()), color=RED, scale_factor=1.1, length=2
            ),
            FadeIn(vert),
        )
        self.pause()
        self.play(
            Indicate(
                VGroup(*graph.lines.values()), color=GREEN, scale_factor=1.1, length=2
            ),
            FadeIn(edges),
        )
        self.pause()

        self.play(
            FadeOut(edges),
            FadeOut(vert),
        )

        graph.match("B", "C")
        graph.match("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.unmatch("B", "C")
        graph.unmatch("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.match("A", "B")
        graph.match("C", "D")
        graph.match("E", "F")
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.unmatch("A", "B")
        graph.unmatch("C", "D")
        graph.unmatch("E", "F")
        self.play(AnimationGroup(*graph.update_matching()))
        graph.match("B", "C")
        graph.match("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))

        self.pause()

        self.play(graph.shift(4 * LEFT))

        self.pause()

        text = [
            MarkupText("Augmenting Path", font_size=32),
            MarkupText(
                "• Path on <i>G = (V, E)</i> w.r.t. some matching <i>M</i>",
                font_size=24,
            ),
            MarkupText("• Begins and ends on unmatched vertices", font_size=24),
            MarkupText(
                "• Alternates edges in <i>M</i> and not in <i>M</i>", font_size=24
            ),
            MarkupText("∴ Must be odd length", font_size=24),
        ]
        text[0].next_to(graph.points["E"], buff=1)
        self.play(Write(text[0]))
        ul = Underline(text[0])
        self.play(Create(ul))
        for i in range(1, len(text)):
            text[i].next_to(text[i - 1], DOWN, aligned_edge=LEFT)

        for line in text[1:-1]:
            self.pause()
            self.play(FadeIn(line))

        self.pause()

        paths = [
            graph.highlight_path(*path)
            for path in [["A", "B", "C", "F"], ["A", "B", "C", "D", "E", "F"]]
        ]

        self.play(Create(paths[0]))
        self.pause()
        self.play(FadeOut(paths[0]))
        self.pause()
        self.play(Create(paths[1]))
        self.pause()
        # self.play(Circumscribe(Dot(radius=1).move_to(graph.lines[("A", "B")].get_center()), shape=Circle, color=BLUE))
        # self.pause()
        # self.play(Circumscribe(Dot(radius=1).move_to(graph.lines[("E", "F")].get_center()), shape=Circle, color=BLUE))
        # self.pause()
        self.play(
            Circumscribe(
                Dot(radius=0.25).move_to(graph.points["A"].get_center()),
                shape=Circle,
                color=BLUE,
            )
        )
        self.pause()
        self.play(
            Circumscribe(
                Dot(radius=0.25).move_to(graph.points["F"].get_center()),
                shape=Circle,
                color=BLUE,
            )
        )
        self.pause()
        self.play(
            Indicate(
                VGroup(graph.lines[("B", "C")], graph.lines[("D", "E")]), color=BLUE
            )
        )
        self.pause()

        self.play(FadeIn(text[-1]))
        self.pause()

        # self.play(FadeOut(paths[1]))
        # self.pause()

        self.play(
            AnimationGroup(
                graph.apply_to_all(FadeOut),
                *[FadeOut(t) for t in text],
                FadeOut(ul),
                FadeOut(paths[1]),
            )
        )
        self.pause()


class MaximumImpliesNoAP(MyScene):
    def construct(self):
        lemma = Group(
            MathTex(r"M \textrm{ is maximum}"),
            MathTex(r"\iff{}"),
            MathTex(r"\nexists \textrm{ augmenting path w.r.t } M"),
        ).arrange(RIGHT)
        self.play(FadeIn(lemma))
        self.pause()

        self.play(Transform(lemma[1], MathTex(r"\Longrightarrow{}").move_to(lemma[1])))

        self.pause()

        self.play(lemma.animate.to_edge(UP, buff=1))
        self.pause()

        graph = _make_even_cycle_graph()
        graph.match("B", "C")
        graph.match("D", "E")
        graph.update_matching(animated=False)
        graph.draw_edges(self)
        graph.draw_points(self)

        path = ["A", "B", "C", "F"]

        path_hl = graph.highlight_path(*path)
        self.play(Create(path_hl))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        augment = MathTex("M", "\oplus{} ", "P").next_to(
            graph.points["C"], direction=DOWN, buff=0.5
        )
        self.play(FadeIn(augment))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching(), FadeOut(path_hl)))
        self.pause()

        self.play(
            AnimationGroup(
                Indicate(augment[0]),
                Indicate(graph.lines[("B", "C")]),
                # Wiggle(graph.lines[("B", "C")]),
                Indicate(graph.lines[("D", "E")]),
                # Wiggle(graph.lines[("D", "E")]),
            )
        )
        self.pause()

        hl = (
            Line(
                augment[2].get_center() + LEFT * 0.25,
                augment[2].get_center() + RIGHT * 0.25,
            )
            .set_stroke(color=YELLOW, width=48, opacity=0.5)
            .set_z_index(-1)
        )
        self.play(AnimationGroup(Create(hl), Create(path_hl)))
        self.pause()
        self.play(FadeOut(hl))
        self.pause()
        augment2 = MathTex(r"|", r"M \oplus{} P", "| > |M|").next_to(
            graph.points["C"], direction=DOWN, buff=0.5
        )
        self.play(augment.animate.move_to(augment2[1]))
        graph.invert_path(*path)
        self.play(
            AnimationGroup(
                FadeIn(augment2),
                FadeOut(augment),
                AnimationGroup(*graph.update_matching()),
            )
        )
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        self.play(
            AnimationGroup(
                graph.apply_to_all(FadeOut),
                FadeOut(path_hl),
                FadeOut(augment2),
            )
        )
        self.pause()


class NoAPImpliesMaximum(MyScene):
    def construct(self):
        lemma = (
            Group(
                MathTex(r"M \textrm{ is maximum}"),
                MathTex(r"\iff{}"),
                MathTex(r"\nexists \textrm{ augmenting path w.r.t } M"),
            )
            .arrange(RIGHT)
            .to_edge(UP, buff=1)
        )
        arrow = MathTex(r"\Longrightarrow{}").move_to(lemma[1])

        self.add(lemma[0], lemma[2], arrow)
        self.play(Rotate(arrow))
        self.pause()

        subtitle = Tex(
            r"By contrapositive: $M$ is not maximum $\Longrightarrow{} M$ has an augmenting path",
            font_size=32,
        ).next_to(lemma, DOWN)
        self.play(FadeIn(subtitle))
        self.pause()

        lines = [
            r"&\textrm{Let }M'\textrm{ be a matching such that }|M'| > |M|\\",
            r"&\textrm{Let }H\leftarrow{} M' + M \equiv (M \cup M' \textrm{ double-counting } M \cap M')\\",
            r"&\forall{} \textrm{ vertex } v \in H \textrm{, } deg_{H}(v) \le{} 2\ (\textrm{At most 1 edge from each of }M, M')\\",
            r"&\textrm{Any connected component of }H\textrm{ must be either a path or a cycle}\\",
            r"&\textrm{Each component of }H\textrm{ must be one of the following: }\\",
            r"&\textrm{(odd cycles impossible)}\\",
            r"&\textrm{Since } |M'| > |M|,",
            r"\ \exists \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ (\ \circ\ >\ \circ\ )",
            r"\equiv \textrm{augmenting path w.r.t. } M",
        ]
        lines = [
            MathTex(s, font_size=32, substrings_to_isolate=["M'", "M", "H", r"\circ"])
            for s in lines
        ]
        for line in lines:
            line.set_color_by_tex("M", YELLOW)
            line.set_color_by_tex("M'", BLUE)
            line.set_color_by_tex("H", LIGHT_BROWN)
            line.set_color_by_tex(r"\circ", BLACK)
        proof = Group(*lines[:-3], Group(*lines[-3:]).arrange(RIGHT, buff=0.2)).arrange(
            DOWN, aligned_edge=LEFT, buff=0.15
        )

        proof.next_to(subtitle, DOWN, buff=0.5).to_edge(LEFT)
        for line in proof[:-2]:
            self.play(FadeIn(line))
            self.pause()

        graph_scale = 0.6

        def g(a):
            return Graph(a, solid_color=YELLOW, dashed_color=BLUE, scale=graph_scale)

        # g1 = Graph({"A": [0, 0, 0]})
        g2 = g(
            {
                "A": [0, 0, 0],
                "B": [1, 0, 0],
                "C": [1, 1, 0],
                "D": [0, 1, 0],
            }
        )
        g2.add_edge("A", "B")
        g2.add_edge("B", "C")
        g2.add_edge("C", "D")
        g2.add_edge("D", "A")
        g2.match("A", "B")
        g2.match("C", "D")
        g2.update_matching(animated=False)

        g3 = g(
            {
                "A": [0, 1, 0],
                "B": [sin(2 * pi / 5), cos(2 * pi / 5), 0],
                "C": [sin(4 * pi / 5), -cos(pi / 5), 0],
                "D": [-sin(4 * pi / 5), -cos(pi / 5), 0],
                "E": [-sin(2 * pi / 5), cos(2 * pi / 5), 0],
            }
        )
        g3.add_edge("A", "B")
        g3.add_edge("B", "C")
        g3.add_edge("C", "D")
        g3.add_edge("D", "E")
        g3.add_edge("E", "A")
        g3.match("A", "B")
        g3.match("C", "D")
        g3.match("E", "A")
        g3.update_matching(animated=False)

        h = 0.2
        step = sqrt(1 - h**2)
        g4 = g(
            {
                "A": [0, 0, 0],
                "B": [step, h, 0],
                "C": [2 * step, 0, 0],
                "D": [3 * step, h, 0],
                "E": [4 * step, 0, 0],
            }
        )
        g4.add_edge("A", "B")
        g4.add_edge("B", "C")
        g4.add_edge("C", "D")
        g4.add_edge("D", "E")
        g4.match("A", "B")
        g4.match("C", "D")
        g4.update_matching(animated=False)

        g5 = g(
            {
                "A": [0, 0, 0],
                "B": [step, h, 0],
                "C": [2 * step, 0, 0],
                "D": [3 * step, h, 0],
                "E": [4 * step, 0, 0],
                "F": [5 * step, h, 0],
            }
        )
        g5.add_edge("A", "B")
        g5.add_edge("B", "C")
        g5.add_edge("C", "D")
        g5.add_edge("D", "E")
        g5.add_edge("E", "F")
        g5.match("A", "B")
        g5.match("C", "D")
        g5.match("E", "F")
        g5.update_matching(animated=False)

        g6 = g(
            {
                "A": [0, 0, 0],
                "B": [step, h, 0],
                "C": [2 * step, 0, 0],
                "D": [3 * step, h, 0],
                "E": [4 * step, 0, 0],
                "F": [5 * step, h, 0],
            }
        )
        g6.add_edge("A", "B")
        g6.add_edge("B", "C")
        g6.add_edge("C", "D")
        g6.add_edge("D", "E")
        g6.add_edge("E", "F")
        g6.match("B", "C")
        g6.match("D", "E")
        g6.update_matching(animated=False)

        vstack = Group(g5.get_group(), g6.get_group()).arrange(DOWN, buff=0.5)

        group = Group(g2.get_group(), g4.get_group(), vstack).arrange(RIGHT, buff=1)

        group.to_edge(DOWN, buff=0.5)

        for g in [g2, g4, g5, g6]:
            g.draw_edges(self)
            g.draw_points(self)

        self.pause()

        self.play(FadeIn(proof[-2]))
        self.pause()

        g3.get_group().to_edge(RIGHT, buff=0.5)
        g3.draw_edges(self)
        g3.draw_points(self)
        self.pause()
        g3.unmatch("E", "A")
        self.play(*g3.update_matching())
        self.pause()
        g3.match("E", "A")
        self.play(*g3.update_matching())
        self.pause()
        g3.unmatch("E", "A")
        self.play(*g3.update_matching())
        self.pause()
        self.play(g3.apply_to_all(FadeOut))
        self.pause()

        self.play(FadeIn(proof[-1][0])),
        self.pause()

        d1 = Dot(radius=0.2, fill_color=BLUE).move_to(proof[-1][1][1])
        d2 = Dot(radius=0.2, fill_color=YELLOW).move_to(proof[-1][1][3])

        g6_copy = g6.get_group().copy()
        self.play(
            AnimationGroup(
                FadeIn(proof[-1][1]),
                FadeIn(d1),
                FadeIn(d2),
                g6_copy.animate.move_to([-5, proof[-1].get_center()[1], 0], LEFT).scale(
                    0.4
                ),
            )
        )
        self.pause()

        self.play(FadeIn(proof[-1][2])),
        self.pause()

        self.play(
            AnimationGroup(
                *[FadeOut(m) for m in [subtitle, proof, d1, d2]],
                g2.apply_to_all(FadeOut),
                g4.apply_to_all(FadeOut),
                g5.apply_to_all(FadeOut),
                g6.apply_to_all(FadeOut),
                FadeOut(g6_copy),
            )
        )
        self.play(Transform(arrow, lemma[1]))


class AugmentAlgorithm(MyScene):
    def construct(self):
        algo = MathTex(
            r"&\textbf{MaximumMatching}(G, M):\\",
            r"&\ \ \ \ M \leftarrow \emptyset\\",
            r"&\ \ \ \ \textbf{While } \exists \textrm{ an augmenting path } P\\",
            r"&\ \ \ \ \ \ \ \ M \leftarrow M \oplus P\\",
            r"&\ \ \ \ \textbf{return } M\\",
        ).to_edge(LEFT, buff=0.5)

        self.play(FadeIn(algo))
        self.pause()

        halts = MathTex(r"\nexists P \Rightarrow M \textrm{ is maximum}", color=YELLOW)
        halts.next_to(algo.get_part_by_tex(r"augmenting path"), RIGHT, buff=0.5)

        monotonic = MathTex(r"|M \oplus P| > |M|", color=YELLOW)
        monotonic.next_to(algo.get_part_by_tex(r"M \oplus P"), RIGHT, buff=0.5)

        l1 = Underline(algo[2], color=YELLOW)
        l2 = Underline(algo[3], color=YELLOW)
        l3 = Underline(algo[4], color=YELLOW)
        self.play(Create(l1))
        self.pause()
        self.play(Create(l2))
        self.pause()
        self.play(Create(l3))
        self.pause()
        self.play(
            FadeOut(l1),
            FadeOut(l2),
            FadeOut(l3),
        )

        self.play(FadeIn(monotonic))
        self.pause()
        self.play(FadeIn(halts))
        self.pause()

        self.play(
            AnimationGroup(
                FadeOut(halts),
                FadeOut(monotonic),
            )
        )
        self.pause()

        self.play(Indicate(algo.get_part_by_tex("While")))
        self.pause()
        self.play(FadeOut(algo))
        self.pause()


class AugmentAlgorithmExample(MyScene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.match("A", "B")
        graph.match("D", "E")
        graph.update_matching(animated=False)
        graph.draw_points(self)
        graph.draw_edges(self)
        self.pause()
        self.play(graph.shift([-3, 0, 0]))
        self.pause()

        algo = VGroup(
            *[
                Tex(x, font_size=32)
                for x in [
                    r"Select an unmatched vertex $v$",
                    r"Perform a DFS from $v$",
                    r"Keep track of the distance travelled",
                    r"— Every odd step, take an edge $\notin M$",
                    r"— Every even step, take an edge $\in M$",
                    r"If you ever find an unmatched vertex at an",
                    r"odd distance, you have an augmenting path",
                ]
            ]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        algo.to_edge(RIGHT, buff=0.5)

        self.play(FadeIn(algo[0]))
        self.play(
            AnimationGroup(
                FocusOn(graph.points["C"].get_center()),
                graph.points["C"].animate.set_fill(YELLOW),
            )
        )
        self.pause()

        self.play(FadeIn(algo[1]))
        self.pause()

        dfs = graph.highlight_path("C", "B", "A")
        self.play(Create(dfs))
        self.play(Uncreate(dfs))
        dfs = graph.highlight_path("C", "D", "E", "F", "C")
        self.play(Create(dfs))
        self.play(Uncreate(dfs))
        self.pause()

        p1 = graph.highlight_path("C", "D")
        self.play(Create(p1))
        self.pause()

        self.play(FadeIn(algo[2]))
        self.pause()
        count = Text("1", color=YELLOW)
        count.next_to(graph.points["D"], UP)
        self.play(FadeIn(count))
        self.pause()

        self.play(FadeIn(algo[3]))
        self.pause()
        self.play(FadeIn(algo[4]))
        self.pause()

        p2 = graph.highlight_path("D", "E")
        self.play(
            AnimationGroup(
                Create(p2),
                Transform(
                    count,
                    Text("2", color=YELLOW).next_to(graph.points["E"], UP + RIGHT),
                ),
            )
        )
        self.pause()

        p3 = graph.highlight_path("E", "F")
        self.play(
            AnimationGroup(
                Create(p3),
                Transform(
                    count, Text("3", color=YELLOW).next_to(graph.points["F"], RIGHT)
                ),
            )
        )
        self.pause()

        self.play(AnimationGroup(FadeIn(algo[5]), FadeIn(algo[6])))
        self.pause()

        self.play(Circumscribe(VGroup(count, graph.points["F"]), Circle, color=BLUE))

        graph.invert_path("C", "D", "E", "F")

        self.play(
            AnimationGroup(
                FadeOut(count),
                graph.points["C"].animate.set_fill(WHITE),
                *graph.update_matching(),
            )
        )
        self.pause()

        self.play(AnimationGroup(*(FadeOut(p) for p in [p1, p2, p3])))
        self.pause()

        graph.unmatch("A", "B")
        graph.unmatch("C", "D")
        graph.unmatch("E", "F")

        self.play(
            AnimationGroup(
                FadeOut(algo),
                graph.shift([3, 0, 0]),
            )
        )
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()


class AugmentAlgorithmCounterexample(MyScene):
    def construct(self):
        graph = Graph(
            {
                "A": [-2 * sin(2 * pi / 5), 2 * cos(2 * pi / 5), 0],
                "B": [0, 2, 0],
                "C": [2 * sin(2 * pi / 5), 2 * cos(2 * pi / 5), 0],
                "D": [2 * sin(4 * pi / 5), -2 * cos(pi / 5), 0],
                "E": [-2 * sin(4 * pi / 5), -2 * cos(pi / 5), 0],
                "F": [-2 * sin(4 * pi / 5) - 2, -2 * cos(pi / 5), 0],
            }
        )
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "A")
        graph.add_edge("E", "F")
        graph.match("B", "C")
        graph.match("D", "E")
        graph.update_matching(animated=False)
        graph.draw_points(self)
        graph.draw_edges(self)
        self.pause()
        p1_points = ["A", "B", "C", "D", "E", "F"]
        p1 = [graph.highlight_path(p1_points[i], p1_points[i + 1]) for i in range(5)]
        directions = {
            "A": UP + LEFT,
            "B": UP,
            "C": UP + RIGHT,
            "D": DOWN + RIGHT,
            "E": DOWN,
            "F": DOWN,
        }
        count = Text("0", color=YELLOW).next_to(graph.points["A"], directions["A"])
        self.play(
            AnimationGroup(
                FocusOn(graph.points["A"].get_center()),
                graph.points["A"].animate.set_fill(YELLOW),
            )
        )
        self.play(Write(count))
        self.pause()
        for i, p in enumerate(p1):
            move_to = p1_points[i + 1]
            self.play(
                AnimationGroup(
                    Create(p),
                    Transform(
                        count,
                        Text(str(i + 1), color=YELLOW).next_to(
                            graph.points[move_to], directions[move_to]
                        ),
                    ),
                )
            )
            self.pause()

        # self.play(AnimationGroup(
        #     *[graph.points[p].animate.set_fill(BLUE_D) for p in p1_points],
        #     *[graph.lines[(p1_points[i], p1_points[i + 1])].animate.set_stroke(BLUE_D) for i in range(5)]
        # ))
        # self.play(AnimationGroup(
        #     *[p.animate.set_stroke(BLUE, opacity=0.7, z_index=-1) for p in p1]
        # ))
        # self.pause()
        # self.play(AnimationGroup(
        #     *[p.animate.set_stroke(YELLOW, opacity=0.5, z_index=-1) for p in p1]
        # ))
        graph_g = graph.get_group()
        graph_g.set_z_index(100)
        p1_solid = graph.highlight_path(*p1_points)
        self.play(
            AnimationGroup(*[FadeOut(p) for p in p1], FadeIn(p1_solid), FadeOut(count))
        )
        self.play(Uncreate(p1_solid))

        count = Text("1", color=YELLOW).next_to(graph.points["E"], directions["E"])

        p2 = graph.highlight_path("A", "E")
        self.play(
            AnimationGroup(
                Create(p2),
                Write(count),
            )
        )
        self.pause()
        p3 = graph.highlight_path("E", "F")
        self.play(Create(p3))
        self.play(Uncreate(p3))
        self.pause()

        p3 = graph.highlight_path("E", "D", "C", "B")
        self.play(
            AnimationGroup(
                Create(p3),
                Transform(
                    count, Text("4", color=YELLOW).next_to(graph.points["B"], DOWN)
                ),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                FadeOut(p2),
                FadeOut(p3),
                FadeOut(count),
            )
        )
        self.pause()


class BipartiteAnimation(MyScene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.draw_edges(self)
        graph.draw_points(self)
        self.pause()
        y = 2
        x = -1
        dx = 1.8
        dy = sqrt(4 - dx**2)
        self.play(
            graph.rearrange(
                {
                    "A": [x + dx, y - 0 * dy, 0],
                    "B": [x, y - 1 * dy, 0],
                    "C": [x + dx, y - 2 * dy, 0],
                    "D": [x, y - 2 * dy, 0],
                    "E": [x + dx, y - 3.5 * dy, 0],
                    "F": [x, y - 3.5 * dy, 0],
                }
            )
        )
        self.pause()

        self.play(
            graph.rearrange(
                {
                    "A": ORIGIN,
                    "B": ORIGIN,
                    "C": ORIGIN,
                    "D": ORIGIN,
                    "E": ORIGIN,
                    "F": ORIGIN,
                }
            )
        )
        self.play(FadeOut(graph.get_group()))
        self.pause()

        text = VGroup(
            *[
                Tex(x)
                for x in [
                    r"Augmenting path matching on a bipartite graph $G=(V, E)$\\",
                    r"|V|=n, |E|=m\\",
                    r"$n/2$ searches\\",
                    r"Each DFS is $O(m)$\\",
                    r"$O(nm)$\\",
                    r"$O(m\sqrt{n})$\\",
                ]
            ]
        ).arrange(DOWN, buff=0.3)
        for line in text:
            self.play(FadeIn(line))
            self.pause()
        self.play(FadeOut(text))
        self.pause()


class BlossomDefinition(MyScene):
    def construct(self):
        graph_points = {
            "A": np.array([-2, 0, 0]),
            "B": np.array([-2 * cos(2 * pi / 5), 2 * sin(2 * pi / 5), 0]),
            "C": np.array([2 * cos(pi / 5), 2 * sin(4 * pi / 5), 0]),
            "D": np.array([2 * cos(pi / 5), -2 * sin(4 * pi / 5), 0]),
            "E": np.array([-2 * cos(2 * pi / 5), -2 * sin(2 * pi / 5), 0]),
            "F": np.array([-4, 0, 0]),
            "G": np.array([-6, 0, 0]),
            "H": np.array([-6, -2, 0]),
            "I": np.array([-4, -2, 0]),
        }
        shift = RIGHT * 3 + DOWN * 0.5
        graph_points = dict((k, v + shift) for (k, v) in graph_points.items())
        graph = Graph(graph_points)
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "A")
        graph.add_edge("A", "F")
        graph.add_edge("F", "G")
        graph.add_edge("G", "H")
        graph.add_edge("H", "I")

        graph_abcde = graph.get_sub_group(["A", "B", "C", "D", "E"])
        graph_abcde.shift(-shift)
        self.play(GrowFromCenter(graph_abcde))
        self.pause()

        blossom = Tex(r"Blossom").to_edge(UP)
        self.play(Write(blossom))
        self.pause()

        self.play(graph_abcde.animate.shift(shift))
        self.pause()

        definition = (
            VGroup(
                *[
                    Tex(x)
                    for x in [
                        r"$\bullet$ Cycle of size $2k+1$\\",
                        r"$\bullet$ $k$ internally matched edges\\",
                        r"$\bullet$ A stem",
                    ]
                ]
            )
            .arrange(DOWN, aligned_edge=LEFT)
            .next_to(blossom, DOWN, buff=0.75)
            .to_edge(LEFT)
        )
        self.play(Write(definition[0]))
        self.pause()

        k_2 = MathTex("k=2").move_to(shift)
        self.play(Write(k_2))
        self.pause()

        graph.match("B", "C")
        graph.match("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        self.play(Write(definition[1]))
        self.pause()

        l1 = graph.get_sub_group(["B", "C"])
        l2 = graph.get_sub_group(["D", "E"])
        self.play(LaggedStart(Indicate(l1), Indicate(l2), lag_ratio=0.2))
        self.pause()

        self.play(FadeOut(k_2))
        self.pause()

        ee = ((graph_points["E"] - shift) * 1.4) + shift
        graph.add_point("ee", ee, hidden=True)
        graph.add_edge("ee", "E")
        self.play(FadeIn(graph.lines[("E", "ee")]))
        self.pause()

        arc_margin = 2 * PI / 40
        arc_a = Arc(
            start_angle=PI - arc_margin,
            angle=2 * arc_margin - (4 * 2 * PI / 5),
            radius=2.5,
            stroke_color=YELLOW,
        ).shift(shift)
        arc_b = Arc(
            start_angle=PI + arc_margin,
            angle=-2 * arc_margin + (1 * 2 * PI / 5),
            radius=2.5,
            stroke_color=YELLOW,
        ).shift(shift)
        aa = ((graph_points["A"] - shift) * 1.4) + shift
        ee_line = graph.lines[("E", "ee")]
        out_delta_a = arc_a.get_end() - ee_line.get_start()
        out_line_a = Arrow(
            ee_line.get_start() + out_delta_a,
            ee_line.get_end() + out_delta_a,
            max_stroke_width_to_length_ratio=999,
            max_tip_length_to_length_ratio=0.3,
            buff=0,
            color=YELLOW,
        )
        in_delta_a = arc_a.get_start() - graph_points["A"]
        in_line_a = Line(aa + in_delta_a, graph_points["A"] + in_delta_a).set_stroke(
            color=YELLOW
        )

        out_delta_b = arc_b.get_end() - ee_line.get_start()
        out_line_b = Arrow(
            ee_line.get_start() + out_delta_b,
            ee_line.get_end() + out_delta_b,
            max_stroke_width_to_length_ratio=999,
            max_tip_length_to_length_ratio=0.3,
            buff=0,
            color=YELLOW,
        )
        in_delta_b = arc_b.get_start() - graph_points["A"]
        in_line_b = Line(aa + in_delta_b, graph_points["A"] + in_delta_b, color=YELLOW)

        self.play(
            LaggedStart(
                Create(VGroup(in_line_a, arc_a, out_line_a)),
                Create(VGroup(in_line_b, arc_b, out_line_b)),
                lag_ratio=0.3,
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                FadeOut(VGroup(in_line_a, arc_a, out_line_a)),
                FadeOut(VGroup(in_line_b, arc_b, out_line_b)),
            )
        )
        self.pause()

        a = graph_points["A"]
        b = graph_points["B"]
        e = graph_points["E"]
        ab = b - a
        ae = e - a
        choice_a = Arrow(
            a - 0.2 * ae,
            a - 0.2 * ae + 0.6 * ab,
            max_tip_length_to_length_ratio=0.3,
            max_stroke_width_to_length_ratio=5,
            color=YELLOW,
            stroke_width=5,
            buff=0.1,
        )
        choice_b = Arrow(
            a - 0.2 * ab,
            a - 0.2 * ab + 0.6 * ae,
            max_tip_length_to_length_ratio=0.3,
            max_stroke_width_to_length_ratio=5,
            color=YELLOW,
            stroke_width=5,
            buff=0.1,
        )
        self.play(
            LaggedStart(
                LaggedStart(
                    FocusOn(graph.points["A"]),
                    graph.points["A"].animate.set_fill(color=YELLOW),
                    lag_ratio=0.4,
                ),
                LaggedStart(GrowArrow(choice_a), GrowArrow(choice_b), lag_ratio=0.2),
                lag_ratio=0.6,
            )
        )
        self.pause()

        graph.points["A"].set_z_index(9999)

        root = Tex("root", color=YELLOW)
        root.next_to(graph.points["A"], RIGHT, buff=0.4)
        self.play(Write(root))
        self.pause()

        self.play(
            AnimationGroup(
                FadeOut(choice_a),
                FadeOut(choice_b),
            )
        )
        self.pause()

        graph.match("A", "F")
        graph.update_matching(animated=False)
        self.play(
            LaggedStart(
                GrowFromPoint(graph.lines[("A", "F")], graph_points["A"]),
                GrowFromCenter(graph.points["F"]),
                lag_ratio=0.3,
            )
        )
        self.pause()

        self.play(Indicate(graph.points["A"]))
        self.pause()

        self.play(
            AnimationGroup(
                FadeOut(graph.lines[("A", "F")]),
                FadeOut(graph.points["F"]),
                FadeOut(graph.lines[("E", "ee")]),
            )
        )
        self.pause()

        stem_text = Tex("stem", color=BLUE).next_to(graph_points["F"], UP, buff=0.4)
        self.play(
            LaggedStart(
                GrowFromPoint(graph.lines[("A", "F")], graph_points["A"]),
                GrowFromCenter(graph.points["F"]),
                GrowFromPoint(graph.lines[("F", "G")], graph_points["F"]),
                GrowFromCenter(graph.points["G"]),
                Write(stem_text),
                lag_ratio=0.3,
            )
        )
        self.pause()

        stem_hl = graph.highlight_path("A", "F", "G").set_stroke(color=BLUE)
        self.play(ShowPassingFlash(stem_hl, time_width=1, time=1.5))
        self.pause()

        stem_text_copy = stem_text.copy()
        self.play(Transform(stem_text_copy, definition[2]))
        self.pause()

        graph.match("G", "H")
        graph.update_matching(animated=False)
        self.play(
            AnimationGroup(
                FadeIn(graph.get_sub_group(["H", "I"])),
                FadeIn(graph.lines[("G", "H")]),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                FadeOut(graph.get_sub_group(["F", "G", "H", "I"])),
                FadeOut(graph.lines[("A", "F")]),
                FadeOut(stem_text),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                FadeIn(graph.points["F"]),
                FadeIn(graph.lines[("A", "F")]),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                FadeOut(graph.points["F"]),
                FadeOut(graph.lines[("A", "F")]),
                graph.points["A"].animate.set_fill(color=WHITE),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                FadeOut(blossom),
                FadeOut(definition),
                FadeOut(stem_text_copy),
                FadeOut(root),
                graph.get_sub_group(["A", "B", "C", "D", "E"]).animate.shift(-shift),
            )
        )
        self.pause()


class BlossomShrinkingAlgorithm(MyScene):
    def construct(self):
        graph_points = {
            "A": np.array([-2, 0, 0]),
            "B": np.array([-2 * cos(2 * pi / 5), 2 * sin(2 * pi / 5), 0]),
            "C": np.array([2 * cos(pi / 5), 2 * sin(4 * pi / 5), 0]),
            "D": np.array([2 * cos(pi / 5), -2 * sin(4 * pi / 5), 0]),
            "E": np.array([-2 * cos(2 * pi / 5), -2 * sin(2 * pi / 5), 0]),
            "X": np.array([-4, 0, 0]),
            "Y": np.array([-6, 0, 0]),
        }
        graph_points["F"] = graph_points["C"] * 1.8
        graph_points["G"] = graph_points["D"] * 1.8
        graph = Graph(graph_points)
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "A")
        graph.add_edge("A", "X")
        graph.add_edge("X", "Y")
        graph.add_edge("C", "F")
        graph.add_edge("D", "G")
        graph.match("B", "C")
        graph.match("D", "E")
        graph.match("A", "X")
        graph.update_matching(animated=False)
        graph.draw_edges(self)
        graph.draw_points(self)
        self.pause()

        self.play(
            graph.rearrange(
                {
                    "F": graph_points["C"] + graph_points["C"] * 0.0001,
                    "G": graph_points["D"] + graph_points["D"] * 0.0001,
                    "X": graph_points["A"] + graph_points["A"] * 0.0001,
                    "Y": graph_points["A"] + graph_points["A"] * 0.0001,
                },
                dont_stretch={
                    ("X", "Y"),
                    ("C", "F"),
                    ("D", "G"),
                },
            )
        )
        self.pause()
        self.play(
            graph.rearrange(
                {
                    "F": graph_points["F"],
                    "G": graph_points["G"],
                    "X": graph_points["X"],
                    "Y": graph_points["Y"],
                },
                dont_stretch={
                    ("X", "Y"),
                    ("C", "F"),
                    ("D", "G"),
                },
            )
        )
        self.pause()

        self.play(Indicate(graph.get_sub_group(["X", "A"])))
        self.pause()

        self.play(
            Circumscribe(
                graph.get_sub_group(["A", "B", "C", "D", "E"]), Circle, color=BLUE
            )
        )
        self.pause()

        self.play(
            graph.rearrange(
                {
                    "A": graph_points["A"] * 0.0001,
                    "B": graph_points["B"] * 0.0001,
                    "C": graph_points["C"] * 0.0001,
                    "D": graph_points["D"] * 0.0001,
                    "E": graph_points["E"] * 0.0001,
                },
                dont_stretch={
                    ("C", "F"),
                    ("D", "G"),
                },
            ),
        )
        self.pause()

        self.play(
            graph.rearrange(
                {
                    "A": graph_points["A"],
                    "B": graph_points["B"],
                    "C": graph_points["C"],
                    "D": graph_points["D"],
                    "E": graph_points["E"],
                },
                dont_stretch={
                    ("C", "F"),
                    ("D", "G"),
                },
            ),
        )
        self.pause()

        path = graph.highlight_path("Y", "X", "A", "E", "D", "C", "B")
        self.play(Create(path))
        self.pause()

        edge_length = 4 * sin(PI / 5)
        circle = (
            Circle(radius=edge_length)
            .set_stroke(color=YELLOW)
            .set_fill(opacity=0)
            .move_to(graph_points["B"])
        )
        self.play(GrowFromCenter(circle))
        self.play(
            AnimationGroup(
                FadeOut(circle),
                Flash(graph.points["A"], flash_radius=0.2, line_length=0.3),
            )
        )
        self.pause()

        def hl(*points):
            return (
                Path(*points)
                .set_stroke(color=YELLOW, width=30, opacity=0.5)
                .set_z_index(-1)
            )

        stem_hl = hl(graph_points["Y"], ORIGIN)

        self.play(
            AnimationGroup(
                Transform(path, stem_hl),
                graph.rearrange(
                    {
                        "A": graph_points["A"] * 0.0001,
                        "B": graph_points["B"] * 0.0001,
                        "C": graph_points["C"] * 0.0001,
                        "D": graph_points["D"] * 0.0001,
                        "E": graph_points["E"] * 0.0001,
                        "X": graph_points["X"],
                        "Y": graph_points["Y"],
                    },
                    dont_stretch={
                        ("C", "F"),
                        ("D", "G"),
                    },
                ),
            )
        )
        self.pause()

        path_cf = graph.highlight_path("C", "F")
        self.play(Create(path_cf))
        self.pause()

        self.play(
            AnimationGroup(
                Transform(path, hl(graph_points["Y"], graph_points["A"])),
                Transform(path_cf, hl(graph_points["C"], graph_points["F"])),
                graph.rearrange(
                    {
                        "A": graph_points["A"],
                        "B": graph_points["B"],
                        "C": graph_points["C"],
                        "D": graph_points["D"],
                        "E": graph_points["E"],
                        "X": graph_points["X"],
                        "Y": graph_points["Y"],
                    },
                    dont_stretch={
                        ("C", "F"),
                        ("D", "G"),
                    },
                ),
            )
        )
        self.pause()

        lifted_path = graph.highlight_path("A", "B", "C")
        self.play(Create(lifted_path))
        self.pause()
        self.play(Transform(lifted_path, graph.highlight_path("A", "E", "D", "C")))
        self.pause()
        self.play(Transform(lifted_path, graph.highlight_path("A", "B", "C")))
        self.pause()


class BlossomShrinkingProof(MyScene):
    def construct(self):
        graph_points = {
            "A": np.array([-1, 0, 0]),
            "B": np.array([-cos(2 * pi / 5), sin(2 * pi / 5), 0]),
            "C": np.array([cos(pi / 5), sin(4 * pi / 5), 0]),
            "D": np.array([cos(pi / 5), -sin(4 * pi / 5), 0]),
            "E": np.array([-cos(2 * pi / 5), -sin(2 * pi / 5), 0]),
        }
        graph_points["X"] = graph_points["A"] * 2
        graph_points["Y"] = graph_points["C"] * 2
        graph_points["Z"] = graph_points["D"] * 2
        graph_points_original = {
            k: v + RIGHT * 4.5 + UP * 2 for (k, v) in graph_points.items()
        }
        graph_original = Graph(graph_points_original, scale=0.8)
        graph_original.add_edge("A", "B")
        graph_original.add_edge("B", "C")
        graph_original.add_edge("C", "D")
        graph_original.add_edge("D", "E")
        graph_original.add_edge("E", "A")
        graph_original.add_edge("A", "X")
        graph_original.add_edge("C", "Y")
        graph_original.add_edge("D", "Z")
        graph_original.match("A", "X")
        graph_original.match("B", "C")
        graph_original.match("D", "E")
        graph_original.update_matching(animated=False)

        graph_points_contracted = {
            "X": graph_points["X"],
            "Y": graph_points["Y"],
            "Z": graph_points["Z"],
            "B": ORIGIN,
        }
        graph_points_contracted = {
            k: v + RIGHT * 4.5 + DOWN * 2 for (k, v) in graph_points_contracted.items()
        }
        graph_contracted = Graph(graph_points_contracted, scale=0.8)
        graph_contracted.add_edge("B", "X")
        graph_contracted.add_edge("B", "Y")
        graph_contracted.add_edge("B", "Z")
        graph_contracted.match("B", "X")
        graph_contracted.update_matching(animated=False)

        proof_lines = [
            (
                0,
                [
                    r"Contract blossom ",
                    r"$B$",
                    r" $\rightarrow$ vertex ",
                    r"$B'$",
                    r" to transform ",
                    r"$M$",
                    r" $\rightarrow$ ",
                    r"$M'$",
                    r" ($|M|>|M'|$)",
                ],
            ),
            (0, [r"$M'$", r" is maximum ", r"$\implies{}$ ", r"$M$", r" is maximum"]),
            (0, r"By contradiction: assume $M'$ is maximum but $M$ isn't."),
            (0, r"$\implies{}$ There must be some augmenting path $P$ w.r.t. $M$"),
            (0, r"3 cases:"),
            (1, r"1. $P$ doesn't intersect $B$"),
            (2, r"$P$ must also exist in $M'$"),
            (2, r"$M'$ is not maximum [contradiction]"),
            (1, r"2. $P$ has an endpoint in $B$"),
            (2, r"A.P. must end on an unmatched vertex"),
            (2, r"A blossom has either $0$ or $1$ unmatched vertices"),
            (2, r"If $P$ ends in $B$, $B$ has 1 unmatched vertex"),
            (2, r"($B'$ is also unmatched)"),
            (2, r"Let $(u,v) \in P : u \in B, v \not\in B$"),
            (
                2,
                r"$(u,v)$ must be unmatched ($\nexists$ matches $B \leftrightarrow  M$)",
            ),
            (2, r"Construct A.P. w.r.t $M'$ with all of $P$ up to $v$, plus $(v, B’)$"),
            (2, r"$M'$ is not maximum [contradiction]"),
            (1, r"3. $P$ passes through $B$"),
            (
                2,
                r"Let $(u_1, v_1), (u_2, v_2) \in P : u_1, u_2 \in B, v_1, v_2 \not\in B$",
            ),
            (2, r"3 cases:"),
            (3, r"$1$. $(u_1, v_1), (u_2, v_2) \in M$"),
            (4, r"Not possible ($B$ has $\le1$ unmatched vertex)"),
            (3, r"$2$. $(u_1, v_1) \in M, (u_2, v_2) \not\in M$"),
            (4, r"Create an A.P. w.r.t. M' by contracting $u_1 = u_2 = B'$"),
            (
                4,
                r"New path is $(P\textrm{ up to }v_1) \rightarrow v_1 \rightarrow B' \rightarrow v_2 \rightarrow (P\textrm{ from }v_2)$",
            ),
            (4, r"$M'$ is not maximum [contradiction]"),
            (3, r"$3$. $(u_1, v_1), (u_2, v_2) \not\in M$"),
            (4, r"If the root of $B$ is unmatched"),
            (5, r"Then $B'$ is unmatched"),
            (
                5,
                r"Construct a new A.P. with $(P\textrm{ up to }v_1) \rightarrow v_1 \rightarrow B'$",
            ),
            (4, r"If the root of $B$ is matched"),
            (5, r"$B'$ is matched with the stem of $P$ "),
            (5.5, "(which must end in an unmatched vertex)"),
            (5, r"Construct a new A.P. with"),
            (
                5.5,
                r"$(P\textrm{ up to }v_1) \rightarrow v_1 \rightarrow B' \rightarrow \textrm{stem}(B)$",
            ),
        ]

        proof_font_size = 28
        proof = (
            VGroup(
                *[
                    Tex(
                        *([tex] if isinstance(tex, str) else tex),
                        font_size=proof_font_size,
                    )
                    for (_, tex) in proof_lines
                ]
            )
            .arrange(DOWN, aligned_edge=LEFT)
            .to_edge(UP)
            .to_edge(LEFT)
        )
        for i, (offset, _) in enumerate(proof_lines):
            proof[i].shift([offset / 2, 0, 0])

        arrow = (
            MathTex(r"\Rightarrow", font_size=64).move_to(RIGHT * 4.5).rotate(-PI / 2)
        )

        self.play(Write(proof[0], time_width=0.2))
        self.pause()
        self.play(GrowFromCenter(graph_original.get_group()))
        self.pause()
        self.play(GrowFromCenter(arrow))
        self.pause()
        self.play(GrowFromCenter(graph_contracted.get_group()))
        self.pause()

        blossom = graph_original.get_sub_group(["A", "B", "C", "D", "E"])
        self.play(
            AnimationGroup(
                Indicate(blossom, color=BLUE, time_width=128),
                Indicate(
                    proof[0].get_part_by_tex("B"),
                    color=BLUE,
                    time_width=128,
                    scale_factor=1.8,
                ),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(
                    graph_contracted.get_sub_group(["B"]),
                    color=BLUE,
                    scale_factor=1.8,
                    time_width=128,
                ),
                Indicate(
                    proof[0].get_part_by_tex("B'"),
                    color=BLUE,
                    time_width=128,
                    scale_factor=1.8,
                ),
            )
        )
        self.pause()

        m = VGroup(
            *(graph_original.points[x] for x in ["X", "A", "B", "C", "D", "E"]),
            *(graph_original.lines[x] for x in graph_original.matching),
        )
        self.play(
            AnimationGroup(
                Indicate(m, time_width=128),
                Indicate(
                    proof[0].get_part_by_tex("M"), time_width=128, scale_factor=1.8
                ),
            )
        )
        self.pause()
        m_prime = VGroup(
            *(graph_contracted.points[x] for x in ["X", "B"]),
            *(graph_contracted.lines[x] for x in graph_contracted.matching),
        )
        self.play(
            AnimationGroup(
                Indicate(m_prime, time_width=128),
                Indicate(
                    proof[0].get_part_by_tex("M'"), time_width=128, scale_factor=1.8
                ),
            )
        )
        self.pause()

        self.play(Write(proof[1], time_width=0.2))
        self.pause()

        self.play(
            AnimationGroup(
                Indicate(m_prime, time_width=128),
                Indicate(
                    proof[1].get_part_by_tex("M'"), time_width=128, scale_factor=1.8
                ),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                Indicate(m, time_width=128),
                Indicate(
                    proof[1].get_part_by_tex("$M$"), time_width=128, scale_factor=1.8
                ),
            )
        )
        self.pause()
        implies = proof[1].get_part_by_tex(r"\implies{}")
        self.play(
            Transform(
                implies,
                Tex("$\Longleftrightarrow$ ", font_size=proof_font_size).move_to(
                    implies
                ),
            )
        )
        self.pause()
        self.play(
            Transform(
                implies,
                Tex("$\implies{}$ ", font_size=proof_font_size).move_to(implies),
            )
        )
        self.pause()

        for x in proof[2:6]:
            self.play(Write(x, time_width=0.2))

        def hl(*points):
            return (
                Path(*points)
                .set_stroke(color=YELLOW, width=30, opacity=0.5)
                .set_z_index(-1)
            )

        path_1_points = [
            RIGHT * 2.5 + UP * 3,
            RIGHT * 3.5 + UP * 3.1,
            RIGHT * 4.5 + UP * 3.7,
            RIGHT * 5.5 + UP * 3.4,
        ]

        path_1 = hl(*path_1_points)
        path_2 = hl(*[x + DOWN * 4 for x in path_1_points])

        self.play(Create(path_1))
        self.pause()

        self.play(Write(proof[6], time_width=0.2))
        self.pause()

        self.play(Create(path_2))
        self.pause()

        self.play(Write(proof[7], time_width=0.2))
        self.pause()

        self.play(
            AnimationGroup(
                Transform(
                    VGroup(proof[6], proof[7]),
                    MathTex(
                        r"\checkmark", font_size=proof_font_size, color=YELLOW
                    ).next_to(proof[5], RIGHT),
                ),
                FadeOut(path_1),
                FadeOut(path_2),
            )
        )
        self.pause()

        line_height = proof[0].get_center()[1] - proof[1].get_center()[1]

        for line in proof[8:]:
            line.shift(2 * line_height * UP)

        self.play(Write(proof[8], time_width=0.2))
        self.pause()

        path_1 = graph_original.highlight_path("A", "B", "C", "Y")
        path_2 = graph_contracted.highlight_path("B", "Y")

        graph_original.unmatch("A", "X")
        graph_contracted.unmatch("B", "X")
        self.play(
            AnimationGroup(
                *graph_original.update_matching(),
                *graph_contracted.update_matching(),
                Create(path_1),
                Create(path_2),
            )
        )
        self.pause()

        for x in proof[9:14]:
            self.play(Write(x, time_width=0.2))

        self.play(Indicate(graph_original.get_sub_group(["C", "Y"]), color=BLUE))
        self.pause()
        for x in proof[14:17]:
            self.play(Write(x, time_width=0.2))
        self.pause()
        self.play(Indicate(graph_contracted.get_sub_group(["B", "Y"]), color=BLUE))
        self.pause()

        self.play(
            AnimationGroup(
                Transform(
                    VGroup(*proof[9:17]),
                    MathTex(
                        r"\checkmark", font_size=proof_font_size, color=YELLOW
                    ).next_to(proof[8], RIGHT),
                ),
                FadeOut(path_1),
                FadeOut(path_2),
            )
        )
        self.pause()

        for line in proof[17:]:
            line.shift(8.25 * line_height * UP)

        self.play(Write(proof[17], time_width=0.2))
        self.pause()

        path_1 = graph_original.highlight_path("X", "A", "B", "C", "Y")
        path_2 = graph_contracted.highlight_path("X", "B", "Y")
        self.play(
            LaggedStart(
                Create(path_1),
                Create(path_2),
            )
        )
        self.pause()

        self.play(Write(proof[18], time_width=0.2))
        self.pause()

        label_size = 32
        u2_label = MathTex(r"u_2", color=BLUE, font_size=label_size).next_to(
            graph_original.points["C"], DOWN + RIGHT, buff=0.1
        )
        v2_label = MathTex(r"v_2", color=BLUE, font_size=label_size).next_to(
            graph_original.points["Y"], DOWN + RIGHT, buff=0.1
        )
        u1_label = MathTex(r"u_1", color=BLUE, font_size=label_size).next_to(
            graph_original.points["A"], DOWN, buff=0.3
        )
        v1_label = MathTex(r"v_1", color=BLUE, font_size=label_size).next_to(
            graph_original.points["X"], DOWN
        )

        v2_label_contracted = MathTex(r"v_2", color=BLUE, font_size=label_size).next_to(
            graph_contracted.points["Y"], DOWN + RIGHT, buff=0.1
        )
        v1_label_contracted = MathTex(r"v_1", color=BLUE, font_size=label_size).next_to(
            graph_contracted.points["X"], DOWN
        )
        b_label_contracted = MathTex(r"B'", color=BLUE, font_size=label_size).next_to(
            graph_contracted.points["B"], DOWN
        )

        self.play(
            LaggedStart(
                Write(u1_label),
                Write(v1_label),
                Write(u2_label),
                Write(v2_label),
                Write(v1_label_contracted),
                Write(v2_label_contracted),
                Write(b_label_contracted),
                lag_ratio=0.2,
            )
        )
        self.pause()

        self.play(AnimationGroup(FadeOut(path_1), FadeOut(path_2), lag_ratio=0.5))
        self.pause()

        self.play(
            LaggedStart(
                Indicate(graph_original.get_sub_group(["X", "A"]), color=BLUE),
                Indicate(graph_original.get_sub_group(["C", "Y"]), color=BLUE),
            )
        )
        self.pause()

        self.play(
            LaggedStart(
                Indicate(graph_contracted.get_sub_group(["X", "B"]), color=BLUE),
                Indicate(graph_contracted.get_sub_group(["B", "Y"]), color=BLUE),
            )
        )
        self.pause()

        self.play(Write(proof[19], time_width=0.2))
        self.pause()

        # 3.1
        self.play(Write(proof[20], time_width=0.2))
        self.pause()

        graph_original.match("X", "A")
        graph_original.match("C", "Y")
        self.play(LaggedStart(*graph_original.update_matching(), lag_ratio=0.2))
        self.pause()

        self.play(Write(proof[21], time_width=0.2))
        self.pause()

        self.play(
            AnimationGroup(
                FocusOn(graph_original.points["C"].get_center()),
                graph_original.lines[("C", "Y")].animate.set_stroke(color=YELLOW),
                graph_original.lines[("B", "C")].animate.set_stroke(color=YELLOW),
            )
        )
        self.play(
            AnimationGroup(
                Wiggle(graph_original.lines[("C", "Y")]),
                Wiggle(graph_original.lines[("B", "C")]),
            )
        )
        self.play(
            AnimationGroup(
                graph_original.lines[("C", "Y")].animate.set_stroke(color=WHITE),
                graph_original.lines[("B", "C")].animate.set_stroke(color=WHITE),
            )
        )
        self.pause()

        self.play(
            Transform(
                proof[21],
                MathTex(r"\checkmark", font_size=proof_font_size, color=YELLOW).next_to(
                    proof[20], RIGHT
                ),
            )
        )
        self.pause()

        for line in proof[22:]:
            line.shift(1 * line_height * UP)

        self.play(Write(proof[22], time_width=0.2))
        self.pause()

        graph_original.unmatch("C", "Y")
        graph_contracted.match("X", "B")
        self.play(
            AnimationGroup(
                *graph_original.update_matching(),
                *graph_contracted.update_matching(),
            )
        )
        self.pause()

        # 3.2
        self.play(Write(proof[23], time_width=0.2))
        self.pause()

        self.play(
            LaggedStart(
                Indicate(graph_original.get_sub_group(["X", "A"]), color=BLUE),
                Indicate(graph_original.get_sub_group(["C", "Y"]), color=BLUE),
            )
        )
        self.pause()
        self.play(
            LaggedStart(
                Indicate(graph_contracted.get_sub_group(["X", "B"]), color=BLUE),
                Indicate(graph_contracted.get_sub_group(["B", "Y"]), color=BLUE),
            )
        )
        self.pause()

        self.play(Write(proof[24], time_width=0.2))
        self.pause()

        path_1 = graph_original.highlight_path("X", "A", "B", "C", "Y")
        path_2 = graph_contracted.highlight_path("X", "B", "Y")
        self.play(
            LaggedStart(
                Create(path_1),
                Create(path_2),
            )
        )
        self.pause()

        graph_original.add_point("XX", graph_original.points["X"].get_center() + LEFT)
        graph_original.add_edge("XX", "X")
        graph_contracted.add_point(
            "XX", graph_contracted.points["X"].get_center() + LEFT
        )
        graph_contracted.add_edge("XX", "X")

        path_1_x = graph_original.highlight_path("X", "XX")
        path_2_x = graph_contracted.highlight_path("X", "XX")

        self.play(
            LaggedStart(
                FadeOut(v2_label),
                FadeOut(v2_label_contracted),
                GrowFromPoint(
                    VGroup(
                        graph_original.points["XX"], graph_original.lines[("X", "XX")]
                    ),
                    graph_original.points["X"].get_center(),
                ),
                GrowFromPoint(
                    VGroup(
                        graph_contracted.points["XX"],
                        graph_contracted.lines[("X", "XX")],
                    ),
                    graph_contracted.points["X"].get_center(),
                ),
            )
        )
        self.pause()
        self.play(
            LaggedStart(
                Create(path_1_x),
                Create(path_2_x),
            )
        )

        self.play(Write(proof[25], time_width=0.2))
        self.pause()

        self.play(
            FadeOut(path_1_x),
            FadeOut(path_2_x),
            FadeOut(path_1),
            FadeOut(path_2),
            FadeOut(graph_original.lines[("X", "XX")]),
            FadeOut(graph_original.points["XX"]),
            FadeOut(graph_contracted.lines[("X", "XX")]),
            FadeOut(graph_contracted.points["XX"]),
            FadeIn(v2_label),
            FadeIn(v2_label_contracted),
            Transform(
                VGroup(*proof[23:26]),
                MathTex(r"\checkmark", font_size=proof_font_size, color=YELLOW).next_to(
                    proof[22], RIGHT
                ),
            ),
        )

        # 3.3

        scroll_amount = UP * 3.8

        for line in proof[26:]:
            line.shift(3 * line_height * UP + scroll_amount)

        self.play(VGroup(proof[:26]).animate.shift(scroll_amount))
        self.pause()

        self.play(Write(proof[26], time_width=0.2))
        self.pause()

        # old_original = graph_original.get_sub_group( ["A", "B", "C", "D", "E", "X", "Y", "Z"] )

        graph_original.add_point(
            "W", graph_original.points["E"].get_center() + DOWN * 0.8 + LEFT * 0.8
        )
        graph_original.add_edge("W", "E")
        # graph_original.unmatch("X", "A")
        graph_original.match("E", "W")
        graph_original.update_matching(animated=False)
        graph_original.unmatch("B", "C")
        graph_original.unmatch("D", "E")
        graph_original.match("C", "D")
        graph_original.match("A", "B")

        self.play(
            # FadeOut(old_original),
            # FadeIn(
            #     graph_original.get_sub_group(["A", "B", "C", "D", "E", "W", "Y", "Z"])
            #     .copy()
            #     .set_z_index(10)
            # ),
            FadeOut(graph_original.points["X"]),
            FadeOut(graph_original.lines[("A", "X")]),
            FadeIn(graph_original.points["W"]),
            FadeIn(graph_original.lines[("E", "W")]),
            *graph_original.update_matching(animated=True, fade=True),
            # FadeOut(graph_original.points["X"]),
            # FadeOut(graph_original.lines[("Z", "X")]),
            v1_label.animate.next_to(graph_original.points["Z"], UP + RIGHT, buff=0.1),
            u1_label.animate.next_to(graph_original.points["D"], UP + RIGHT, buff=0.1),
            v1_label_contracted.animate.next_to(
                graph_contracted.points["Z"], UP + RIGHT, buff=0.1
            ),
        )
        self.remove(graph_original)
        self.pause()

        path = graph_original.highlight_path("Y", "C", "D", "Z")
        self.play(Create(path))
        self.pause()

        self.play(FocusOn(graph_original.points["E"].get_center()))
        self.pause()

        self.play(Indicate(graph_original.get_sub_group(["W", "E"])))
        self.pause()

        graph_contracted.add_point(
            "XXX", graph_contracted.points["X"].get_center() + DOWN
        )
        graph_contracted.add_edge("XXX", "X")

        graph_original.add_point("WW", graph_original.points["W"].get_center() + LEFT)
        graph_original.add_edge("W", "WW")
        self.play(
            LaggedStart(
                GrowFromPoint(
                    VGroup(
                        graph_original.points["WW"], graph_original.lines[("W", "WW")]
                    ),
                    graph_original.points["W"].get_center(),
                ),
                GrowFromPoint(
                    VGroup(
                        graph_contracted.points["XXX"],
                        graph_contracted.lines[("X", "XXX")],
                    ),
                    graph_contracted.points["X"].get_center(),
                ),
            )
        )
        self.pause()

        path2 = graph_contracted.highlight_path("Y", "B", "X", "XXX")
        self.play(Create(path2))
        self.pause()

        for line in proof[27:]:
            self.play(Write(line, time_width=0.2))
            self.pause()

        self.play(
            Transform(
                VGroup(*proof[27:]),
                MathTex(r"\checkmark", font_size=proof_font_size, color=YELLOW).next_to(
                    proof[26], RIGHT
                ),
            )
        )
        self.pause()
        self.play(proof.animate.shift(-scroll_amount))
        self.pause()

        self.pause()
        self.pause()


class WeightedMatching(MyScene):
    def construct(self):
        vspace = 1.5
        graph_points = {
            "A": [0, 2 * vspace, 1],
            "B": [0, vspace, 1],
            "C": [0, 0, 1],
            "X": [3, 1.5 * vspace, 1],
            "Y": [3, 0.5 * vspace, 1],
            # "Z": [3, 0, 1],
        }
        graph = Graph(graph_points)
        graph.get_group().move_to(ORIGIN)

        graph.add_edge("A", "X")
        graph.add_edge("A", "Y")
        graph.add_edge("B", "X")
        graph.add_edge("C", "Y")

        weights = [
            MathTex("55", font_size=42).move_to(
                graph.points["X"].get_center() + 0.8 * UP + 1.5 * LEFT
            ),
            MathTex("45", font_size=42).move_to(
                graph.points["B"].get_center() + 0.6 * UP + 0.5 * RIGHT
            ),
            MathTex("89", font_size=42).move_to(
                graph.points["Y"].get_center() + 0.75 * UP + 0.3 * LEFT
            ),
            MathTex("60", font_size=42).move_to(
                graph.points["C"].get_center() + 0.8 * UP + 1.2 * RIGHT
            ),
        ]

        circs = [
            get_bounding_rect(x, buff=0.1, stroke_color=YELLOW, stroke_width=5)
            for x in weights
        ]

        equation = MathTex(
            r"55 + 60 &= 115\\",
            r"45 + 89 &= 134",
        ).to_edge(RIGHT, buff=1)

        graph.draw_points(self)
        graph.draw_edges(self)
        self.pause()
        self.play(LaggedStart(*[Write(x) for x in weights], lag_ratio=0.2))
        self.pause()

        graph.match("A", "X")
        graph.match("C", "Y")
        self.play(*graph.update_matching())
        self.pause()

        self.play(
            LaggedStart(
                Create(circs[0]), Create(circs[3]), Write(equation[0]), lag_ratio=0.2
            )
        )
        self.pause()

        graph.unmatch("A", "X")
        graph.unmatch("C", "Y")
        self.play(
            *graph.update_matching(),
            FadeOut(circs[0]),
            FadeOut(circs[3]),
        )
        self.pause()

        graph.match("B", "X")
        graph.match("A", "Y")
        self.play(*graph.update_matching())
        self.pause()

        self.play(
            LaggedStart(
                Create(circs[1]), Create(circs[2]), Write(equation[1]), lag_ratio=0.2
            )
        )
        self.pause()

        # self.play(graph.get_group().animate.to_edge(UP, buff=.7))
        # self.pause()


class LinearProgrammingReframing(MyScene):
    def construct(self):
        vspace = 1.5
        graph_points = {
            "A": [0, 2 * vspace, 1],
            "B": [0, vspace, 1],
            "C": [0, 0, 1],
            "X": [3, 1.5 * vspace, 1],
            "Y": [3, 0.5 * vspace, 1],
            # "Z": [3, 0, 1],
        }
        graph = Graph(
            graph_points
        )  # , unconnected_edge=lambda p1, p2, **kwargs: Line(p1, p2, stroke_width=5, stroke_color=WHITE, **kwargs))
        graph.get_group().move_to(ORIGIN).to_edge(UP, buff=0.7)

        graph.add_edge("A", "X")
        graph.add_edge("A", "Y")
        graph.add_edge("B", "X")
        graph.add_edge("C", "Y")

        weights = [
            MathTex("55", font_size=42).move_to(
                graph.points["X"].get_center() + 0.8 * UP + 1.5 * LEFT
            ),
            MathTex("45", font_size=42).move_to(
                graph.points["B"].get_center() + 0.6 * UP + 0.5 * RIGHT
            ),
            MathTex("89", font_size=42).move_to(
                graph.points["Y"].get_center() + 0.75 * UP + 0.3 * LEFT
            ),
            MathTex("60", font_size=42).move_to(
                graph.points["C"].get_center() + 0.8 * UP + 1.2 * RIGHT
            ),
        ]

        sum = MathTex("55", "+", "60", "=", "115", font_size=42, color=YELLOW).next_to(
            graph.get_group(), DOWN
        )

        self.play(FadeIn(graph.get_group()), *[FadeIn(w) for w in weights])

        self.pause()
        graph.match("A", "X")
        graph.match("C", "Y")
        self.play(*graph.update_matching())
        self.pause()

        self.play(
            weights[0].animate.set_fill(color=YELLOW),
            weights[3].animate.set_fill(color=YELLOW),
        )
        self.pause()

        weights_0_copy = weights[0].copy()
        weights_3_copy = weights[3].copy()

        self.play(
            LaggedStart(
                weights_0_copy.animate.move_to(sum[0]),
                weights_3_copy.animate.move_to(sum[2]),
                FadeIn(VGroup(sum[1], sum[3], sum[4])),
            )
        )
        self.pause()

        graph.unmatch("A", "X")
        graph.unmatch("C", "Y")
        graph.match("A", "Y")
        graph.match("B", "X")

        self.play(
            *graph.update_matching(),
            weights[0].animate.set_fill(color=WHITE),
            weights[3].animate.set_fill(color=WHITE),
        )
        self.pause()

        self.play(
            weights[1].animate.set_fill(color=YELLOW),
            weights[2].animate.set_fill(color=YELLOW),
        )
        self.pause()

        weights_1_copy = weights[1].copy()
        weights_2_copy = weights[2].copy()
        self.play(
            LaggedStart(
                FadeOut(weights_0_copy),
                FadeOut(weights_3_copy),
                weights_1_copy.animate.move_to(sum[0]),
                weights_2_copy.animate.move_to(sum[2]),
                Transform(
                    sum[4], MathTex("134", font_size=42, color=YELLOW).move_to(sum[4])
                ),
            )
        )
        self.pause()

        self.play(
            FadeOut(sum[1]),
            FadeOut(sum[3]),
            FadeOut(sum[4]),
            FadeOut(weights_1_copy),
            FadeOut(weights_2_copy),
            weights[1].animate.set_fill(color=WHITE),
            weights[2].animate.set_fill(color=WHITE),
        )
        self.pause()

        tex = MathTex(
            r"\textrm{maximize } & ",
            r"\sum\nolimits_{e\in E}{",
            r"w_e",
            r"x_e",
            r"}\\",
            r"\textrm{subject to } & ",
            r"\sum\nolimits_",
            r"{e\in E:v \in e}",
            r"{x_e} \le 1 \textrm{ }",
            r"\forall v \in V\\",
            r"\textrm{and } & x_e \in \{0, 1\} \textrm{ }\forall e \in E\\",
        )

        tex.next_to(graph.get_group(), DOWN, buff=0.7)

        self.play(AnimationGroup(*[FadeIn(x) for x in tex[:5]]))
        self.pause()

        self.play(Indicate(tex[2]), *[Indicate(w) for w in weights])
        self.pause()
        self.play(
            Indicate(tex[3]),
            Indicate(graph.lines[("A", "Y")]),
            Indicate(graph.lines[("B", "X")]),
        )
        self.pause()
        self.play(
            Indicate(VGroup(*tex[2:4])),
            Indicate(weights[1]),
            Indicate(weights[2]),
        )
        self.pause()
        self.play(Indicate(tex[1]), *[Indicate(line) for line in graph.lines.values()])
        self.pause()

        self.play(AnimationGroup(*[FadeIn(x) for x in tex[5:10]]))
        self.pause()
        self.play(Indicate(tex[9]))
        self.pause()
        self.play(Circumscribe(tex[6:9]))
        self.pause()
        self.play(
            LaggedStart(*(Indicate(x) for x in graph.points.values()), lag_ratio=0.15)
        )
        self.pause()
        self.play(Indicate(tex[7]))
        self.pause()
        self.play(Indicate(tex[8]))
        self.pause()
        self.play(AnimationGroup(*[FadeIn(x) for x in tex[10]]))
        self.pause()

        self.pause()
        self.pause()
        self.pause()


class LPTitleCard(MyScene):
    def construct(self):
        title = Tex("Linear Programming", font_size=64)
        self.play(Write(title))
        self.pause()
        self.play(Transform(title, Tex("Linear Planning", font_size=64)))
        self.pause()
        self.play(
            Transform(title, Tex(r"Optimizing with\\ linear constraints", font_size=64))
        )
        self.pause()
        self.play(FadeOut(title))
        self.pause()


class LinearProgrammingIntro(MyScene):
    def construct(self):
        optimize = Tex("Optimize:")
        function = MathTex(r"f(x,y)=180x+200y")
        subject_to = Tex("Subject to constraints:")
        constraint_tex = MathTex(
            r"5x+4y & \le 80\\",
            r"10x+20y & \le 220\\",
            r"x & \ge 0\\",
            r"y & \ge 0\\",
        )
        spacer = (
            Rectangle(width=0, height=0.5)
            .set_stroke(color=None, width=0)
            .set_fill(color=None)
        )
        g = VGroup(optimize, function, spacer, subject_to, constraint_tex).arrange(
            DOWN, buff=0.3
        )
        optimize.shift(LEFT * 3)
        subject_to.align_to(optimize, LEFT)
        self.play(
            AnimationGroup(
                FadeIn(optimize),
                FadeIn(function),
            )
        )
        self.pause()
        self.play(
            Transform(optimize, Tex("Maximize:").move_to(optimize, aligned_edge=LEFT))
        )
        self.pause()
        self.play(
            LaggedStart(
                FadeIn(subject_to), *[FadeIn(x) for x in constraint_tex], lag_ratio=0.6
            )
        )
        self.pause()
        self.play(FadeOut(g))
        self.pause()

        problem_lines = [
            (0, "Carpenter maximizing proffit"),
            (0, r"$\bullet$ Tables take"),
            (1, [r"10", r" units of lumber,"]),
            (1, [r"5", r" hours of labor."]),
            (1, [r"Make ", r"\$180", r" proffit"]),
            (0, r"$\bullet$ Bookshelves take"),
            (1, [r"20", r" units of lumber,"]),
            (1, [r"4", r" hours of labor."]),
            (1, [r"Make ", r"\$200", r" proffit"]),
            (0, [r"$\bullet$ ", r"220 units of lumber available"]),
            (0, [r"$\bullet$ ", r"80 hours of labor available"]),
        ]

        colors = [
            (r"10", RED),
            (r"20", RED),
            (r"5", GREEN),
            (r"4", GREEN),
            (r"220 units", RED),
            (r"80 hours", GREEN),
            (r"\$180", YELLOW),
            (r"\$200", YELLOW),
        ]

        problem_tex = VGroup(
            *[
                Tex(*([tex] if isinstance(tex, str) else tex))
                for (_, tex) in problem_lines
            ]
        ).arrange(DOWN, aligned_edge=LEFT)
        for i, (offset, _) in enumerate(problem_lines):
            problem_tex[i].shift([offset / 2, 0, 0])
            for tex, color in colors:
                problem_tex[i].set_color_by_tex(tex, color)

        self.play(FadeIn(problem_tex[0]))
        self.pause()
        for line in problem_tex[1:]:
            self.play(FadeIn(line))
            self.pause()

        self.play(problem_tex.animate.to_edge(LEFT))

        function = (
            MathTex("f(x,y)=", "180", "x", "+", "200", "y")
            .set_color_by_tex("180", YELLOW)
            .set_color_by_tex("200", YELLOW)
        )
        function.move_to((3.8, 2, 1))

        self.play(FadeIn(function[0]))
        self.pause()

        self.play(
            AnimationGroup(
                FadeIn(function[2]),
                Transform(
                    problem_tex[4].get_part_by_tex("180").copy(),
                    function.get_part_by_tex("180"),
                ),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                FadeIn(function[3]),
                FadeIn(function[5]),
                Transform(
                    problem_tex[8].get_part_by_tex("200").copy(),
                    function.get_part_by_tex("200"),
                ),
            )
        )
        self.pause()

        constraint_tex = MathTex(
            r"10",
            r"x",
            r"+",
            r"20",
            r"y",
            r" & \le ",
            r"220\\",
            r"5",
            r"x",
            r"+",
            r"4",
            r"y",
            r" & \le ",
            r"80\\",
            r"x & \ge 0\\",
            r"y & \ge 0\\",
        ).next_to(function, DOWN, buff=0.6)

        colors = [
            (r"10", RED),
            (r"20", RED),
            (r"220", RED),
            (r"5", GREEN),
            (r"4", GREEN),
            (r"80", GREEN),
        ]
        for tex, color in colors:
            constraint_tex.set_color_by_tex(tex, color)

        # first iniequality
        self.play(
            AnimationGroup(
                FadeIn(constraint_tex.get_part_by_tex("x")),
                Transform(
                    problem_tex[2].get_part_by_tex("10").copy(),
                    constraint_tex.get_part_by_tex("10"),
                ),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                FadeIn(constraint_tex.get_part_by_tex("+")),
                FadeIn(constraint_tex.get_part_by_tex("y")),
                Transform(
                    problem_tex[6].get_part_by_tex("20").copy(),
                    constraint_tex.get_part_by_tex("20"),
                ),
            )
        )
        self.pause()
        self.play(
            AnimationGroup(
                FadeIn(constraint_tex[5]),  # <=
                Transform(
                    problem_tex[9].get_part_by_tex("220").copy(),
                    constraint_tex.get_part_by_tex("220"),
                ),
            )
        )
        self.pause()

        # second inequality
        self.play(
            AnimationGroup(
                FadeIn(constraint_tex[8]),  # x
                Transform(
                    problem_tex[3].get_part_by_tex("5").copy(),
                    constraint_tex.get_part_by_tex("5"),
                ),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                FadeIn(constraint_tex[9]),  # +
                FadeIn(constraint_tex[11]),  # y
                Transform(
                    problem_tex[7].get_part_by_tex("4").copy(),
                    constraint_tex.get_part_by_tex("4"),
                ),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                FadeIn(constraint_tex[12]),  # <=
                Transform(
                    problem_tex[10].get_part_by_tex("80").copy(),
                    constraint_tex.get_part_by_tex("80"),
                ),
            )
        )
        self.pause()

        self.play(
            LaggedStart(
                FadeIn(constraint_tex[14]),
                FadeIn(constraint_tex[15]),
            )
        )
        self.pause()


class LinearProgrammingGraph(MyScene):
    def construct(self):
        x_range = [-3, 25]
        y_range = [-3, 20]
        x_axis_ticks = [x for x in range(x_range[0], x_range[1] + 1) if x % 5 == 0]
        y_axis_ticks = [y for y in range(y_range[0], y_range[1] + 1) if y % 5 == 0]
        unit_size = 0.2
        ax = (
            Axes(
                x_range=x_range + [1],
                y_range=y_range + [1],
                tips=False,
                x_length=unit_size * x_range[1] - x_range[0],
                y_length=unit_size * y_range[1] - y_range[0],
                axis_config={"include_numbers": True, "tick_size": 0.07},
                x_axis_config={
                    "numbers_to_include": x_axis_ticks,
                    "numbers_with_elongated_ticks": x_axis_ticks,
                },
                y_axis_config={
                    "numbers_to_include": y_axis_ticks,
                    "numbers_with_elongated_ticks": y_axis_ticks,
                },
            )
            .to_edge(LEFT, buff=0.75)
            .to_edge(UP, buff=0.25)
            .set_z_index(10)
        )

        self.add(ax)
        self.pause()

        x_label = Tex("Tables", font_size=38).next_to(ax[0], DOWN, buff=0.5)
        y_label = (
            Tex("Bookshelves", font_size=38)
            .rotate(PI / 2)
            .next_to(ax[1], LEFT, buff=0.5)
        )
        self.play(Write(x_label))
        self.pause()
        self.play(Write(y_label))
        self.pause()

        point = Dot(ax.coords_to_point(5, 10), color=YELLOW, radius=0.1)
        lines = ax.get_lines_to_point(ax.c2p(5, 10))
        value = MathTex(
            r"180x+200y", "=", str(180 * 5 + 200 * 10), color=YELLOW
        ).next_to(point, RIGHT)
        self.play(
            AnimationGroup(
                Create(point),
                Create(lines),
            )
        )
        self.pause()
        self.play(Write(value))
        self.pause()

        p2 = ax.c2p(15, 5)
        lines_2 = ax.get_lines_to_point(p2)
        value_2 = MathTex(
            r"180x+200y", "=", str(180 * 15 + 200 * 5), color=YELLOW
        ).next_to(Dot(p2, radius=0.1), RIGHT)
        self.play(
            AnimationGroup(
                point.animate.move_to(p2),
                Transform(lines, lines_2),
                Transform(value, value_2),
            )
        )
        self.pause()

        equation = MathTex(r"f(x,y)=", r"180x+220y", color=YELLOW)

        constraint_tex = (
            MathTex(
                r"5x+4y & \le 80\\",
                r"10x+20y & \le 220\\",
                r"x & \ge 0\\",
                r"y & \ge 0\\",
            )
            .set_color_by_tex("5x", RED)
            .set_color_by_tex("10x", GREEN)
        )

        solution = MathTex("x=", "12", ",y=", "5", color=YELLOW)

        VGroup(equation, constraint_tex, solution).arrange(DOWN).to_edge(
            UP, buff=0.5
        ).to_edge(RIGHT, buff=0.3)

        self.play(
            AnimationGroup(
                FadeOut(lines),
                FadeOut(point),
                FadeOut(value[1]),
                FadeOut(value[2]),
                FadeIn(equation[0]),
                value[0].animate.move_to(equation[1]),
            )
        )
        self.pause()

        self.play(Write(constraint_tex[0]))
        self.pause()

        line_1 = ax.plot(lambda x: (80 - 5 * x) / 4, x_range=[0, 18.4], color=RED)
        points = [
            line_1.get_point_from_function(0),
            line_1.get_point_from_function(18.4),
            ax.c2p(x_range[1], y_range[0]),
            ax.c2p(x_range[1], y_range[1]),
        ]
        area_1 = Polygon(*points, fill_color=RED, stroke_width=0, fill_opacity=0.5)
        self.play(LaggedStart(Create(line_1), FadeIn(area_1), lag_ratio=0.4))
        self.pause()

        self.play(Write(constraint_tex[1]))
        self.pause()
        line_2_func = lambda x: (220 - 10 * x) / 20
        line_2 = ax.plot(line_2_func, x_range=x_range, color=GREEN)
        points = [
            line_2.get_point_from_function(x_range[0]),
            line_2.get_point_from_function(x_range[1]),
            ax.c2p(x_range[1], y_range[1]),
            ax.c2p(x_range[0], y_range[1]),
        ]
        area_2 = Polygon(*points, fill_color=GREEN, stroke_width=0, fill_opacity=0.5)
        self.play(LaggedStart(Create(line_2), FadeIn(area_2), lag_ratio=0.4))
        self.pause()
        area_3 = Polygon(
            ax.c2p(x_range[0], 0),
            ax.c2p(x_range[1], 0),
            ax.c2p(x_range[1], y_range[0]),
            ax.c2p(x_range[0], y_range[0]),
            fill_color=BLUE,
            stroke_width=0,
            fill_opacity=0.5,
        )
        area_4 = Polygon(
            ax.c2p(0, y_range[0]),
            ax.c2p(0, y_range[1]),
            ax.c2p(x_range[0], y_range[1]),
            ax.c2p(x_range[0], y_range[0]),
            fill_color=BLUE,
            stroke_width=0,
            fill_opacity=0.5,
        )

        self.play(
            LaggedStart(
                Write(constraint_tex[2]),
                FadeIn(area_4),
                Write(constraint_tex[3]),
                FadeIn(area_3),
                lag_ratio=0.2,
            )
        )
        self.pause()

        region_coords = [
            (0, 0),
            (0, line_2_func(0)),
            (12, line_2_func(12)),
            (16, 0),
        ]

        region_points = [
            ax.c2p(*p)
            for p in region_coords
            # ax.c2p(0, 0),
            # line_2.get_point_from_function(0),
            # line_2.get_point_from_function(12),
            # ax.c2p(16, 0),
        ]
        region = Polygon(*region_points, stroke_width=10, stroke_color=WHITE)
        self.play(Create(region))
        self.pause()
        self.play(Indicate(region, color=WHITE))
        self.pause()

        point = Dot(ax.c2p(5, 5), color=YELLOW, radius=0.1)
        lines = ax.get_lines_to_point(ax.c2p(5, 5))
        value = MathTex(str(180 * 5 + 200 * 10), color=YELLOW).next_to(point, RIGHT)
        self.play(
            AnimationGroup(
                Create(point),
                Create(lines),
                Write(value),
            )
        )
        self.pause()

        points = [(10, 3), (1, 1), (3, 7)]
        for p in points:
            p2 = ax.c2p(*p)
            lines_new = ax.get_lines_to_point(p2)
            value_new = MathTex(
                str(round(180 * p[0] + 200 * p[1])), color=YELLOW
            ).next_to(Dot(p2, radius=0.1), RIGHT)
            self.play(
                AnimationGroup(
                    point.animate.move_to(p2),
                    Transform(lines, lines_new),
                    Transform(value, value_new),
                )
            )
            self.pause()

        self.play(
            AnimationGroup(
                FadeOut(lines),
                FadeOut(value),
                FadeOut(point),
                region.animate.set_stroke(width=2),
            )
        )
        self.pause()

        dots = []
        corners = region_points[2:] + region_points[:2]
        for p in corners:
            dots.append(
                Circle(radius=0.2, stroke_width=4, stroke_color=WHITE).move_to(p)
            )

        self.play(LaggedStart(*[Create(x) for x in dots], lag_ratio=0.1))
        self.pause()

        yellow_dots = []
        yellow_dot_text = []
        for point in region_coords:
            dot = Dot(radius=0.15, color=YELLOW).move_to(ax.c2p(*point))
            yellow_dots.append(dot)
            yellow_dot_text.append(
                MathTex(
                    str(round(180 * point[0] + 200 * point[1])), color=YELLOW
                ).next_to(dot, UR)
            )

        self.play(LaggedStart(Create(yellow_dots[0]), Write(yellow_dot_text[0])))
        self.pause()
        self.play(
            AnimationGroup(
                ShrinkToCenter(yellow_dots[0]),
                ShrinkToCenter(dots[2]),
                FadeOut(yellow_dot_text[0]),
            )
        )
        self.pause()

        self.play(
            LaggedStart(
                *[
                    LaggedStart(
                        Create(yellow_dots[i]),
                        Write(yellow_dot_text[i]),
                        lag_ratio=0.2,
                    )
                    for i in range(1, 4)
                ],
                lag_ratio=0.2,
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                ShrinkToCenter(yellow_dots[1]),
                ShrinkToCenter(dots[3]),
                FadeOut(yellow_dot_text[1]),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                ShrinkToCenter(yellow_dots[3]),
                ShrinkToCenter(dots[1]),
                FadeOut(yellow_dot_text[3]),
            )
        )
        self.pause()

        lines = ax.get_lines_to_point(region_points[2])
        twelve = MathTex("12", color=YELLOW).move_to(ax.c2p(12, -1))
        five = MathTex("5", color=YELLOW).move_to(ax.c2p(-1, 5))
        self.play(
            LaggedStart(
                Create(lines),
                Write(five),
                Write(twelve),
            )
        )

        self.pause()

        self.play(
            LaggedStart(
                Write(solution[0]),
                Transform(twelve, solution[1]),
                Write(solution[2]),
                Transform(five, solution[3]),
            )
        )
        self.pause()

        self.play(
            AnimationGroup(
                FadeOut(lines),
                FadeOut(yellow_dots[2]),
                FadeOut(dots[0]),
                FadeOut(yellow_dot_text[2]),
            )
        )
        self.pause()

        circles = []
        for y in range(y_range[0], y_range[1] + 1):
            for x in range(x_range[0], x_range[1] + 1):
                value = 180 * x + 200 * y
                p = ax.c2p(x, y)
                circle = Circle(
                    radius=abs(value / 100000) * 1.4, stroke_color=WHITE
                ).move_to(p)
                circles.append(circle)
        self.play(LaggedStart(*[Create(x) for x in circles], lag_ratio=0.001))
        self.pause()
        self.pause()

        arrows = []
        for y in range(y_range[0], y_range[1] + 1):
            for x in range(x_range[0], x_range[1] + 1):
                direction = (180 * RIGHT + 200 * UP) / 1000
                value = abs(180 * x + 200 * y)
                p = ax.c2p(x, y)
                arrow = Arrow(p, p + direction)  # * (.5 + value / 10000))
                arrows.append(arrow)

        self.play(
            LaggedStart(
                *[Transform(c, a) for (c, a) in zip(circles, arrows)], lag_ratio=0.001
            )
        )
        self.pause()

        self.play(
            LaggedStart(
                *[ShrinkToCenter(a) for a in reversed(circles)], lag_ratio=0.001
            )
        )
        self.pause()

        point = ax.c2p(5, 4)
        point = Dot(point, color=WHITE, radius=0.1)
        self.play(GrowFromCenter(point))
        self.pause()

        slope = -180 / 200
        line = ax.plot(
            lambda x: slope * x - 5 * slope + 4,
            x_range=[x_range[0], 12.778],
            color=WHITE,
        )
        self.play(GrowFromCenter(line))
        self.pause()

        arrow = Arrow(
            point.get_center(),
            point.get_center() + (180 * RIGHT + 200 * UP) / 300,
            buff=0,
        )
        self.play(GrowArrow(arrow))
        self.pause()

        region_coords = [
            (-3, 11.2),
            (12.778, -3),
            (x_range[1], y_range[0]),
            (x_range[1], y_range[1]),
            (x_range[0], y_range[1]),
        ]
        region_points = [ax.c2p(*p) for p in region_coords]
        region1 = Polygon(*region_points, stroke_width=0, fill_color=WHITE)
        region_coords = [
            (-3, 11.2),
            (12.778, -3),
            (x_range[0], y_range[0]),
        ]
        region_points = [ax.c2p(*p) for p in region_coords]
        region2 = Polygon(*region_points, stroke_width=0, fill_color=WHITE)

        self.play(Blink(region1, opacity=0.5))
        self.pause()
        self.play(Blink(region2, opacity=0.5))
        self.pause()

        line2 = ax.plot(
            lambda x: slope * x - 7.5 * slope + 6.5,
            x_range=[x_range[0], 18.056],
            color=WHITE,
        )
        self.play(Transform(line.copy(), line2))
        self.pause()

        line3 = ax.plot(
            lambda x: slope * x - 12 * slope + 5,
            x_range=[x_range[0], 20.889],
            color=WHITE,
        )
        self.play(Transform(line2.copy(), line3))
        self.pause()

        self.play(Create(dots[0]))

        self.pause()
        self.pause()
        self.pause()


class LPRelaxation(MyScene):
    def construct(self):
        original = MathTex(
            r"\textrm{max } & ",
            r"\sum\nolimits_{e\in E}{w_e x_e}\\",
            r"\textrm{s.t. } & ",
            r"\sum\nolimits_{e\in E:v \in e}{x_e} \le 1 \textrm{ }",
            r"\forall v \in V\\",
            r"\textrm{and } & ",
            r"x_e \in ",
            r"\{",
            r"0, 1",
            r"\}",
            r" \textrm{ }\forall e \in E\\",
        ).to_edge(UP, 1)
        self.add(original)
        self.pause()
        self.play(original.animate.to_edge(LEFT, 0.7))
        self.pause()

        longform = MathTex(
            r"&w_1 x_1 + w_2 x_2 + w_3 x_3 + \cdots\\",
            r"&x_{01} + x_{02} + x_{02} + \cdots \le 1\\",
            r"&x_{11} + x_{12} + x_{12} + \cdots \le 1\\",
            r"&x_{21} + x_{22} + x_{22} + \cdots \le 1\\",
            r"&\cdots\\",
            r"&0 \le x_{1} \le 1\\",
            r"&0 \le x_{2} \le 1\\",
            r"&0 \le x_{3} \le 1\\",
            r"&\cdots\\",
        ).next_to(original, RIGHT, aligned_edge=UP, buff=0.6)

        cursor = (
            Triangle(fill_color=YELLOW, fill_opacity=1, stroke_width=0)
            .rotate(-90 * DEGREES)
            .scale(0.22)
            .next_to(original[0], LEFT, buff=0.2)
        )
        self.play(FadeIn(cursor))
        self.pause()

        self.play(Transform(original[1].copy(), longform[0]))
        self.pause()

        self.play(cursor.animate.next_to(original[2], LEFT, buff=0.2))
        self.pause()

        self.play(Transform(original[3].copy(), longform[1]))
        self.pause()
        self.play(Transform(original[3].copy(), longform[2]))
        self.pause()
        self.play(Transform(original[3].copy(), longform[3]))
        self.pause()
        self.play(Transform(original[3].copy(), longform[4]))
        self.pause()

        self.play(cursor.animate.next_to(original[5], LEFT, buff=0.2))
        self.pause()

        x_in_01 = original[6:10]
        self.play(Circumscribe(x_in_01))
        self.pause()
        lh = 0.7
        new_x_bound = [
            original[6].copy(),
            original[8].copy(),
            original[7].copy(),
            original[9].copy(),
        ]
        self.play(
            new_x_bound[0].animate.shift(DOWN * lh),
            new_x_bound[1].animate.shift(DOWN * lh),
            Transform(
                new_x_bound[2], MathTex(r"[").move_to(original[7]).shift(DOWN * lh)
            ),
            Transform(
                new_x_bound[3], MathTex(r"]").move_to(original[9]).shift(DOWN * lh)
            ),
        )
        self.pause()
        strike = Line(
            [x_in_01.get_left()[0], x_in_01.get_bottom()[1], 1],
            [x_in_01.get_right()[0], x_in_01.get_top()[1], 1],
            stroke_color=YELLOW,
        )
        self.play(Create(strike))
        self.pause()

        for i in range(4):
            self.play(Transform(VGroup(*new_x_bound).copy(), longform[5 + i]))
            self.pause()
        self.pause()

        self.play(FadeOut(cursor))
        self.pause()

        top_left = np.array([longform[0].get_left()[0], longform[0].get_top()[1], 1])

        variables_arrow = Arrow(
            top_left + 0.5 * UP, top_left + 0.5 * UP + 5 * RIGHT, color=YELLOW, buff=0
        )
        self.play(GrowArrow(variables_arrow))
        self.pause()

        constraints_arrow = Arrow(
            top_left + 0.5 * LEFT,
            top_left + 0.5 * LEFT + 6.5 * DOWN,
            color=YELLOW,
            buff=0,
        )
        self.play(GrowArrow(constraints_arrow))
        self.pause()
        self.pause()


class LPIntegrality(MyScene):
    def construct(self):
        claim = Tex(
            r"\raggedright Claim:\\\hspace{.3cm}",
            r"At least one solution to the relaxed\\\hspace{.3cm}maximum-matching linear program\\\hspace{.3cm}will be integral ",
            r"if the graph is bipartite",
        )
        for line in claim:
            self.play(Write(line))
            self.pause()

        self.play(claim.animate.shift(UP * 5.25))
        self.remove(claim)
        self.pause()

        perfect_matching_tex = Tex("perfect matching", font_size=64)
        max_weight_tex = Tex("maximum-weight", font_size=64)
        perf_matching_tex_grpup = VGroup(max_weight_tex, perfect_matching_tex).arrange(
            RIGHT
        )
        perfect_matching_tex_pos = perfect_matching_tex.get_center()
        perfect_matching_tex.move_to(ORIGIN)

        self.play(Write(perfect_matching_tex))
        self.pause()

        self.play(
            LaggedStart(
                perfect_matching_tex.animate.move_to(perfect_matching_tex_pos),
                FadeIn(max_weight_tex),
                lag_ratio=0.5,
            )
        )
        self.pause()

        self.play(perf_matching_tex_grpup.animate.shift(UP * 5.25))
        self.remove(perf_matching_tex_grpup)
        self.pause()
