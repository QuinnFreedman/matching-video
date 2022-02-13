from asyncio import shield
from calendar import c
from manim import *
from manim.animation.animation import DEFAULT_ANIMATION_RUN_TIME
from manim.mobject.opengl_compatibility import ConvertToOpenGL
from manim_presentation import Slide #as MyScene
from typing import Callable, Iterable, Optional, Sequence
from math import sin, cos, pi, sqrt


# class MyScene(Slide):
#     def __init__(self, *args, **kwargs):
#         super(MyScene, self).__init__(*args, **kwargs)
    
class MyScene(Scene):
    def __init__(self, *args, **kwargs):
        super(MyScene, self).__init__(*args, **kwargs)
    
    def pause(self):
        self.wait(0.25)


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


class Path(VMobject, metaclass=ConvertToOpenGL):
    def __init__(self, *points: Sequence[float], color=BLUE, **kwargs):
        super().__init__(color=color, **kwargs)

        first_vertex, *vertices = points

        self.start_new_path(np.array(first_vertex))
        self.add_points_as_corners(
            [np.array(vertex) for vertex in vertices],
        )


class Graph:
    def __init__(self, points, scale=1, solid_color=WHITE, dashed_color=WHITE):
        self.points = {label: Dot(p, radius=.15*scale) for (label, p) in points.items()}
        self.edges = set()
        self.matching = set()
        self.lines = {}
        self.scale=scale
        self.solid_color = solid_color
        self.dashed_color = dashed_color

    def get_group(self):
        return VGroup(
            *self.points.values(),
            *self.lines.values(),
        )
        
    def get_sub_group(self, vertices):
        points = [self.points[v] for v in vertices]
        edges = [self.lines[e] for e in self.edges if e[0] in vertices and e[1] in vertices]
        return Group(*points, *edges)

    def draw_points(self, scene):
        scene.add(*self.points.values())

    def apply_to_all(self, animation, **kwargs):
        return AnimationGroup(
            *[animation(p) for p in self.points.values()],
            *[animation(l) for l in self.lines.values()],
            **kwargs
        )

    def shift(self, delta, animate=True):
        if animate:
            return AnimationGroup(
                *[p.animate.move_to(p.get_center() + delta) for p in self.points.values()],
                *[l.animate.put_start_and_end_on(l.get_start() + delta, l.get_end() + delta) for l in self.lines.values()]
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
        self.points[label] = Dot(p, radius=0 if hidden else .15*self.scale)

    def UnconnectedEdge(self, p1, p2):
            return DashedLine(p1, p2, stroke_width=10*self.scale, dash_length=0.1*self.scale, dashed_ratio=0.4, stroke_color=self.dashed_color)
            
    def ConnectedEdge(self, p1, p2):
            return Line(p1, p2, stroke_width=10*self.scale, stroke_color=self.solid_color)

    def _make_edge(self, edge):
        p1 = self.points[edge[0]].get_center()
        p2 = self.points[edge[1]].get_center()
        if edge in self.matching:
            return self.ConnectedEdge(p1, p2)
        else:
            return self.UnconnectedEdge(p1, p2)
        
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

    def update_matching(self, animated=True):
        animations = []
        for edge in self.edges:
            old_line = self.lines[edge]
            new_line = self._make_edge(edge)
            if old_line.__class__.__name__ != new_line.__class__.__name__:
                self.lines[edge] = new_line
                if animated:
                    if isinstance(new_line, DashedLine):
                        animations.append(AnimationGroup(
                            FadeIn(new_line, time=0),
                            ShrinkToCenter(old_line),
                        ))
                    else:
                        animations.append(AnimationGroup(
                            GrowFromCenter(new_line),
                            FadeOut(old_line, time=0),
                        ))

        return animations if animated else None

    def rearrange(self, new_points):
        return AnimationGroup(
            *[dot.animate.move_to(new_points[key]) for key, dot in self.points.items()],
            *[self.lines[edge].animate.put_start_and_end_on(new_points[edge[0]], new_points[edge[1]]) for edge in self.edges],
        )

    def highlight_path(self, *points):
        line_points = [self.points[x].get_center() for x in points]
        line = Path(*line_points).set_stroke(color=YELLOW, width=30, opacity=0.5).set_z_index(-1)
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
    graph = Graph({
        "A": [-2,  1, 0],
        "B": [-2, -1, 0],
        "C": [ 0, -1, 0],
        "D": [ 0,  1, 0],
        "E": [ 2,  1, 0],
        "F": [ 2, -1, 0],
        })
        
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "D")
    graph.add_edge("D", "E")
    graph.add_edge("E", "F")
    graph.add_edge("F", "C")
    return graph


def make_matte(w, h):
    bg = Rectangle(width=10,  height=10).set_fill(color=BLACK, opacity=0.5).set_stroke(width=0)
    bg2 = Rectangle(width=w, height=h).set_fill(color=BLACK, opacity=1).set_stroke(width=0)
    outline = Rectangle(width=w, height=h).set_stroke(color=WHITE)
    return (
        AnimationGroup(
            FadeIn(bg),
            FadeIn(bg2),
            Create(outline)
        ),
        AnimationGroup(
            FadeOut(bg),
            FadeOut(bg2),
            FadeOut(outline)
        )
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
            ]
        ]

        grid = VGroup(
            *text[0],
            *text[1]
        ).arrange_in_grid(cols=2, flow_order="dr", col_widths=[3]*2, row_heights=[2]*3)
    
        self.play(FadeIn(grid))
        self.pause()
        self.play(Circumscribe(VGroup(*text[0]), time_width=0.5, buff=0.2))
        self.pause()
        self.play(Circumscribe(VGroup(*text[1]), time_width=0.5, buff=0.2))
        self.pause()

        def edge(a, b):
            return Arrow(text[a[0]][a[1]].get_center(), text[b[0]][b[1]].get_center(), buff=0.5)

        matching1 = [
            edge((0,0), (1,1)),
            edge((0,1), (1,2)),
            edge((0,2), (1,0)),
        ]

        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching1],
            lag_ratio=0.25
        ))
        self.pause()
        self.play(LaggedStart(
            *[FadeOut(a) for a in matching1],
            lag_ratio=0.15
        ))
        self.pause()

        matching2 = [
            edge((0,0), (1,0)),
            edge((0,1), (1,1)),
            edge((0,2), (1,2)),
        ]

        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching2],
            lag_ratio=0.25
        ))
        self.pause()
        self.play(LaggedStart(
            *[FadeOut(a) for a in matching2],
            lag_ratio=0.15
        ))
        self.pause()

        show, hide = make_matte(8, 2)
        popup_text = Group(
            Text("1. Evaluate potential pairings", font_size=32),
            Text("2. Find optimal matching", font_size=32)
        ).arrange(DOWN, aligned_edge=LEFT)

        self.play(LaggedStart(
            show,
            Write(popup_text[0]),
            lag_ratio=0.2
            ))
        self.pause()
        self.play(Write(popup_text[1]))
        self.pause()

        self.play(LaggedStart(
            FadeOut(popup_text[0]),
            popup_text[1].animate.move_to([
                popup_text[1].get_center()[0],
                popup_text[0].get_center()[1],
                0
            ])
        ))
        self.pause()

        popup_text_2 = Group(
            Text("Stable\nmatching", should_center=True, font_size=36, line_spacing=.5),
            Line([0, -.5, 0], [0, .5, 0]),
            Text("Maximum\nmatching", should_center=True, font_size=36, line_spacing=.5),
        ).arrange(RIGHT, buff=.8)
        
        self.play(LaggedStart(
            FadeOut(popup_text[1]),
            FadeIn(popup_text_2),
            lag_ratio=0.4
        ))
        self.pause()
        self.play(Indicate(popup_text_2[0]))
        self.pause()

        self.play(AnimationGroup(
            hide,
            FadeOut(popup_text_2)
            ))
        self.pause()

        pref_squares = [
            VGroup(*[Square(.26) for _ in range(3)])
                .set_stroke(width=2)
                .set_fill(color=BLACK, opacity=1)
                .arrange(DOWN, buff=0)
                .next_to(letter, direction=LEFT if i == 0 else RIGHT)
                .set_z_index(-1)
            for i, column in enumerate(text) for letter in column 
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
            [MathTex(s, font_size=24).move_to(pref_squares[i][j]) for j, s in enumerate(pref)] for i, pref in enumerate(prefs)
        ]

        self.play(LaggedStart(
            *[Create(prefs) for prefs in pref_squares[0]],
            lag_ratio=0.2
        ))
        self.play(LaggedStart(
            *[Write(x) for x in prefs_mtext[0]],
            lag_ratio=0.4
        ))
        self.pause()

        self.play(LaggedStart(
            *[Create(prefs) for prefs in pref_squares[1:3]],
            *[Write(x) for pref_group in prefs_mtext[1:3] for x in pref_group],
            lag_ratio=0.3
        ))
        self.pause()

        self.play(LaggedStart(
            *[Create(prefs) for prefs in pref_squares[3:]],
            *[Write(x) for pref_group in prefs_mtext[3:] for x in pref_group],
            lag_ratio=0.3
        ))
        self.pause()

        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][0]),
            IndicateEdges(pref_squares[0][0], scale_factor=1.5),
        ))
        self.pause()
        self.play(AnimationGroup(
            Indicate(prefs_mtext[3][1]),
            IndicateEdges(pref_squares[3][1], scale_factor=1.5),
        ))
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

        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching1],
            lag_ratio=0.25
        ))
        self.pause()

        self.play(LaggedStart(
            Indicate(text[0][0]),
            Indicate(text[1][0]),
            lag_ratio=0.8
        ))
        self.pause()
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][1]),
            Indicate(prefs_mtext[3][2]),
            IndicateEdges(pref_squares[0][1], scale_factor=1.5),
            IndicateEdges(pref_squares[3][2], scale_factor=1.5),
            Indicate(matching1[0]),
            Indicate(matching1[2]),
        ))
        self.pause()
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][0]),
            Indicate(prefs_mtext[3][1]),
            IndicateEdges(pref_squares[0][0], scale_factor=1.5),
            IndicateEdges(pref_squares[3][1], scale_factor=1.5),
        ))
        self.pause()

        matching1[0].set_z_index(-1)
        matching1[2].set_z_index(-1)
        self.play(AnimationGroup(
            matching1[0].animate.set_stroke(color=GRAY_E).set_fill(color=GRAY_E),
            matching1[2].animate.set_stroke(color=GRAY_E).set_fill(color=GRAY_E),
        ))
        self.pause()

        self.play(Circumscribe(
            VGroup(text[0][0], text[1][0], *prefs_mtext[0], *prefs_mtext[3])
        ))
        self.pause()

        extra_edge = edge((0,0), (1,0))
        self.play(GrowArrow(extra_edge))
        self.pause()
        
        self.play(AnimationGroup(
            Indicate(text[0][2]),
            Indicate(text[1][1])
        ))
        self.pause()

        self.play(AnimationGroup(
            *[FadeOut(a) for a in matching1],
            FadeOut(extra_edge)
        ))
        self.pause()

        matching3 = [
            edge((0,0), (1,1)),
            edge((0,1), (1,0)),
            edge((0,2), (1,2)),
        ]
        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching3],
            lag_ratio=0.25
        ))
        self.pause()
        
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][1]),
            IndicateEdges(pref_squares[0][1], scale_factor=1.5),
            Indicate(matching3[0])
        ))
        self.pause()
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][0]),
            IndicateEdges(pref_squares[0][0], scale_factor=1.5),
        ))
        self.pause()
        self.play(AnimationGroup(
            Indicate(prefs_mtext[3][0]),
            IndicateEdges(pref_squares[3][0], scale_factor=1.5),
            Indicate(matching3[1])
        ))
        self.pause()
        self.play(AnimationGroup(
            *(FadeOut(x) for y in prefs_mtext for x in y),
            *(FadeOut(x) for x in pref_squares),
            *(FadeOut(x) for x in matching3)
        ))
        self.pause()


class StableVsMaximumTable(MyScene):
    def construct(self):
        stable = Tex("Stable Matching", font_size=64).move_to([-3.5, 0, 0])
        maximum = Tex("Maximum Matching", font_size=64).move_to([3.5, 0, 0])
        vline = Line([0, .6, 0], [0, -5.5, 0])
        titles = VGroup(stable, vline, maximum).to_edge(UP, buff=1)
        hline = Line([-7.5, 0, 0], [7.5, 0, 0])
        hline.align_to(maximum.get_critical_point(DOWN) + DOWN * .3, DOWN)

        def bullet(str):
            return Tex(
            r"""
            \begin{itemize}
              \item """ + str + r"""
            \end{itemize}
            """
            )

        list_left = VGroup(
              bullet(r"Anyone can be matched\\with anyone"),
              bullet(r"Everyone will be matched"),
              bullet(r"Preference ranking"),
              bullet(r"Maximize stability"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=.5).align_to([-6.7, 0, 0], LEFT).align_to(hline.get_center() + DOWN * .6, UP)

        list_right = VGroup(
            bullet(r"Not everyone can be\\matched"),
            bullet(r"Maximize number of\\individuals matched"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=.5).align_to([.5, 0, 0], LEFT).align_to(hline.get_center() + DOWN * .6, UP)

        self.play(LaggedStart(
            Create(hline),
            Create(vline),
            Write(stable),
            lag_ratio=.2
        ))

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
            ]
        ]

        grid = VGroup(
            *text[0],
            *text[1]
        ).arrange_in_grid(cols=2, flow_order="dr", col_widths=[3]*2, row_heights=[2]*3)
        self.add(grid)
        self.pause()

        p_a = text[0][0].get_center()
        p_b = text[0][1].get_center()
        p_c = text[0][2].get_center()
        p_1 = text[1][0].get_center()
        p_2 = text[1][1].get_center()
        p_3 = text[1][2].get_center()

        def dashed_line(p1, p2):
            return DashedLine(p1, p2, stroke_width=10, dash_length=0.1, dashed_ratio=0.4, buff=.5, stroke_color=GRAY_D)
            
        def solid_line(p1, p2):
            return Line(p1, p2, stroke_width=10, buff=.5, z_index=10)

        edges = [
            dashed_line(p_a, p_1),
            dashed_line(p_a, p_2),
            dashed_line(p_b, p_2),
            dashed_line(p_b, p_3),
            dashed_line(p_c, p_2),
        ]
        self.play(AnimationGroup(
            *(FadeIn(e) for e in edges)
        ))
        self.pause()

        l1 = solid_line(p_a, p_1)
        l2 = solid_line(p_b, p_2)
        self.play(AnimationGroup(
            GrowFromCenter(l1),
            FadeOut(edges[0]),
        ))
        self.pause()

        self.play(AnimationGroup(
            GrowFromCenter(l2),
            FadeOut(edges[2]),
        ))
        self.pause()

        self.play(Indicate(text[0][2]))
        self.pause()

        self.play(AnimationGroup(
            ShrinkToCenter(l1),
            ShrinkToCenter(l2),
            FadeIn(edges[0]),
            FadeIn(edges[2]),
        ))
        self.pause()
        
        l1 = solid_line(p_a, p_1)
        l3 = solid_line(p_b, p_3)
        l4 = solid_line(p_c, p_2)
        self.play(LaggedStart(
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
            lag_ratio=0.25
        ))
        self.pause()

        self.play(AnimationGroup(
            ShrinkToCenter(l1),
            ShrinkToCenter(l3),
            ShrinkToCenter(l4),
            FadeIn(edges[0]),
            FadeIn(edges[3]),
            FadeIn(edges[4]),
        ))
        self.pause()

        p_a += LEFT
        p_b += LEFT
        p_c += LEFT
        p_1 += RIGHT
        p_2 += RIGHT
        p_3 += RIGHT

        self.play(AnimationGroup(
            *[t.animate.shift(LEFT) for t in text[0]],
            *[t.animate.shift(RIGHT) for t in text[1]],
            # *[e.animate.put_start_and_end_on(e.get_start() + LEFT, e.get_end() + RIGHT) for e in edges]
            # *[Transform(e, dashed_line(e.get_start() + LEFT, e.get_end() + RIGHT)) for e in edges]
            Transform(edges[0], dashed_line(p_a, p_1)),
            Transform(edges[1], dashed_line(p_a, p_2)),
            Transform(edges[2], dashed_line(p_b, p_2)),
            Transform(edges[3], dashed_line(p_b, p_3)),
            Transform(edges[4], dashed_line(p_c, p_2)),
        ))
        self.pause()

        arrows = [Arrow(e.get_start(), e.get_end(), buff=0) for e in edges]
        self.play(LaggedStart(
            *[
                AnimationGroup(
                    FadeOut(edges[i]),
                    GrowArrow(arrows[i]),
                ) for i in range(len(edges))
            ],
            lag_ratio=0.2
        ))

        capacities = [
            MathTex("0", "/", "1", font_size=36).next_to(edges[0].get_center(), direction=UP),
            MathTex("0", "/", "1", font_size=36).next_to(edges[1].get_end() + .25*UP, direction=UP+LEFT, buff=.5),
            MathTex("0", "/", "1", font_size=36).next_to(edges[2].get_center(), direction=UP),
            MathTex("0", "/", "1", font_size=36).next_to(edges[4].get_end() + .25*DOWN, direction=DOWN+LEFT, buff=.5),
            MathTex("0", "/", "1", font_size=36).next_to(edges[3].get_end(), direction=LEFT, buff=1),
        ]

        self.play(LaggedStart(
            *[Write(x) for x in capacities],
            lag_ratio=0.15
        ))
        self.pause()

        def set_fill(capacities, i, s):
            return Transform(capacities[i][0], MathTex(s, font_size=36).move_to(capacities[i][0]))

        self.play(set_fill(capacities, 0, "1"))
        self.pause()
        self.play(set_fill(capacities, 0, "0"))
        self.pause()

        source = MathTex("s", font_size=64).next_to(p_b, direction=LEFT, buff=3)
        sink = MathTex("t", font_size=64).next_to(p_2, direction=RIGHT, buff=3)
        p_s = source.get_center()
        p_t = sink.get_center()

        st_arrows = [
            Arrow(p_s, p_a, buff=.5),
            Arrow(p_s, p_b, buff=.5),
            Arrow(p_s, p_c, buff=.5),
            Arrow(p_1, p_t, buff=.5),
            Arrow(p_2, p_t, buff=.5),
            Arrow(p_3, p_t, buff=.5),
        ]

        st_capacities = [
            MathTex("0", "/", "1", font_size=36).next_to(arrow.get_center(), direction=UP)
            for arrow in st_arrows
        ]

        self.play(LaggedStart(
            Write(source),
            *[GrowArrow(x) for x in st_arrows[:3]],
            *[Write(x) for x in st_capacities[:3]],
            lag_ratio=0.15
        ))
        self.pause()

        self.play(LaggedStart(
            Write(sink),
            *[GrowArrow(x) for x in st_arrows[3:]],
            *[Write(x) for x in st_capacities[3:]],
            lag_ratio=0.15
        ))
        self.pause()

        for obj in arrows + st_arrows + text[0] + text[1] + [source, sink]:
            obj.set_z_index(10)
        
        flow1 = Path(p_s, p_a, p_1, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow1, run_time=1.6),
            set_fill(st_capacities, 0, "1"),
            set_fill(capacities, 0, "1"),
            set_fill(st_capacities, 3, "1"),
            lag_ratio=0.15
        ))
        self.pause()

        flow2 = Path(p_s, p_b, p_3, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow2, run_time=1.6),
            set_fill(st_capacities, 1, "1"),
            set_fill(capacities, 4, "1"),
            set_fill(st_capacities, 5, "1"),
            lag_ratio=0.15
        ))
        self.pause()

        flow3 = Path(p_s, p_c, p_2, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow3, run_time=1.6),
            set_fill(st_capacities, 2, "1"),
            set_fill(capacities, 3, "1"),
            set_fill(st_capacities, 4, "1"),
            lag_ratio=0.15
        ))
        self.pause()

        self.play(Circumscribe(VGroup(VGroup(*st_capacities[:3])), buff=.2))
        self.pause()
        self.play(Circumscribe(VGroup(VGroup(*text[0])), buff=.2))
        self.pause()
        self.play(Circumscribe(VGroup(VGroup(*st_capacities[3:])), buff=.2))
        self.pause()
        self.play(Circumscribe(VGroup(VGroup(*text[1])), buff=.2))
        self.pause()

        flow_direction = Arrow(p_a + UP, p_1 + UP, color=YELLOW)
        self.play(GrowArrow(flow_direction))
        self.pause()
        self.play(FadeOut(flow_direction))
        self.pause()
        
        self.play(Circumscribe(VGroup(VGroup(*text[1])), buff=.2))
        self.pause()
        self.play(LaggedStart(
            *(Indicate(a) for a in st_arrows[3:]),
            lag_ratio=0.15
        ))
        self.pause()
        flow_direction = Arrow([00, 0, 0], [1, 0, 0], color=YELLOW, ).set_stroke(width=8).next_to(sink, DOWN, buff=.3)
        self.play(GrowArrow(flow_direction))
        self.pause()
        self.play(FadeOut(flow_direction))
        self.pause()

        self.play(AnimationGroup(
            *[set_fill(capacities, i, 0) for i in range(len(capacities))],
            *[set_fill(st_capacities, i, 0) for i in range(len(st_capacities))],
            FadeOut(flow1),
            FadeOut(flow2),
            FadeOut(flow3),
        ))
        self.pause()

        def set_cap(capacities, i, s):
            return Transform(capacities[i][2], MathTex(s, font_size=36).move_to(capacities[i][2]))
            
        self.play(AnimationGroup(
            *[set_cap(st_capacities, i, "2") for i in range(3, 6)]
        ))
        self.pause()

        flow1 = Path(p_s, p_a, p_2, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow1, run_time=1.6),
            set_fill(st_capacities, 0, "1"),
            set_fill(capacities, 1, "1"),
            set_fill(st_capacities, 4, "1"),
            lag_ratio=0.15
        ))
        self.pause()
        flow2 = Path(p_s, p_c, p_2, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow2, run_time=1.6),
            set_fill(st_capacities, 2, "1"),
            set_fill(capacities, 3, "1"),
            set_fill(st_capacities, 4, "2"),
            lag_ratio=0.15
        ))
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

        self.play(AnimationGroup(
            *[set_fill(capacities, i, 0) for i in range(len(capacities))],
            *[set_fill(st_capacities, i, 0) for i in range(len(st_capacities))],
            *[set_cap(st_capacities, i, 1) for i in range(len(st_capacities))],
            FadeOut(flow1),
            FadeOut(flow2),
            # FadeOut(flow3),
        ))
        self.pause()

        self.play(AnimationGroup(
            *[set_cap(st_capacities, i, "2") for i in range(3)]
        ))
        self.pause()

        flow1 = Path(p_s, p_b, p_2, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow1, run_time=1.6),
            set_fill(st_capacities, 1, "1"),
            set_fill(capacities, 2, "1"),
            set_fill(st_capacities, 4, "1"),
            lag_ratio=0.15
        ))
        self.pause()
        flow2 = Path(p_s, p_b, p_3, p_t).set_stroke(color=BLUE, opacity=.5, width=20)
        self.play(LaggedStart(
            Create(flow2, run_time=1.6),
            set_fill(st_capacities, 1, "2"),
            set_fill(capacities, 3, "1"),
            set_fill(st_capacities, 5, "1"),
            lag_ratio=0.15
        ))
        self.pause()
        # self.play(AnimationGroup(
        #     *[set_cap(st_capacities, i, "1") for i in range(3)],
        #     *[set_fill(capacities, i, 0) for i in range(len(capacities))],
        #     *[set_fill(st_capacities, i, 0) for i in range(len(st_capacities))],
        #     FadeOut(flow1),
        #     FadeOut(flow2),
        # ))
        # self.pause()
        everything = VGroup(*arrows, *st_arrows, *capacities, *st_capacities, grid, source, sink)
        self.play(AnimationGroup(
            FadeOut(everything),
            FadeOut(flow1),
            FadeOut(flow2),
        ))
        self.pause()


class FourProblems(MyScene):
    def construct(self):
        graph_scale = .6
        def scale_map(map, scalar):
            return {k: [scalar * x for x in v] for k, v in map.items()}

        def make_general_graph():
            g = Graph(scale_map({
                "A": [ 0,            1,           0],
                "B": [ sin(2*pi/5),  cos(2*pi/5), 0],
                "C": [ sin(4*pi/5), -cos(  pi/5), 0],
                "D": [-sin(4*pi/5), -cos(  pi/5), 0],
                "E": [-sin(2*pi/5),  cos(2*pi/5), 0],
                "F": [0,             0,           0],
            }, graph_scale), scale=graph_scale)

            vertices = ["A", "B", "C", "D", "E"]
            for i in range(5):
                g.add_edge(vertices[i], vertices[(i+1)%5])
                g.match(vertices[i], vertices[(i+1)%5])
                g.add_edge(vertices[i], "F")
                g.match(vertices[i], "F")
            
            return g

        def make_bipartite_graph():
            g = Graph(scale_map({
                "A": [0, 0, 0],
                "B": [0, 1, 0],
                "C": [0, 2, 0],
                "D": [1.5, 0, 0],
                "E": [1.5, 1, 0],
                "F": [1.5, 2, 0],
            }, graph_scale), scale=graph_scale)

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

        weighted = Tex("Weighted").move_to([-.15, -grid_size * 2, 0])
        unweighted = Tex("Unweighted").move_to([0, -grid_size, 0]).align_to(weighted, RIGHT)

        lines = [
            Line([0.5 * grid_size, 0.5 * grid_size, 0], [0.5 * grid_size, -2.5 * grid_size, 0]),
            Line([1.5 * grid_size, 0.5 * grid_size, 0], [1.5 * grid_size, -2.5 * grid_size, 0]),
            Line([-0.5 * grid_size, -0.5 * grid_size, 0], [2.5 * grid_size, -0.5 * grid_size, 0]),
            Line([-0.5 * grid_size, -1.5 * grid_size, 0], [2.5 * grid_size, -1.5 * grid_size, 0]),
        ]
        numbers = [
            MathTex("1", font_size=72).move_to([    grid_size,     -grid_size, 0]),
            MathTex("2", font_size=72).move_to([2 * grid_size,     -grid_size, 0]),
            MathTex("3", font_size=72).move_to([    grid_size, -2 * grid_size, 0]),
            MathTex("4", font_size=72).move_to([2 * grid_size, -2 * grid_size, 0]),
        ]
        cursor = Square(grid_size - 0.1, stroke_color=YELLOW, stroke_width=10).move_to([grid_size, -grid_size, 0])
        all = Group(general.get_group(), bipartite.get_group(), unweighted, weighted, *lines, cursor, *numbers).move_to(ORIGIN)
        
        self.play(LaggedStart(
            *[Create(x) for x in lines],
            lag_ratio=.2
        ))
        self.pause()
        self.play(bipartite.apply_to_all(lambda x: Create(x, run_time=.5), lag_ratio=.1))
        self.pause()
        self.play(general.apply_to_all(lambda x: Create(x, run_time=.5), lag_ratio=.1))
        self.pause()
        self.play(Write(unweighted))
        self.pause()
        self.play(Write(weighted))
        self.pause()

        self.play(Create(cursor))
        self.pause()

        self.play(LaggedStart(
            *[Write(x) for x in numbers],
            lag_ratio=.4
        ))


class AugmentingPath(MyScene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.draw_points(self)
        graph.draw_edges(self)

        self.pause()

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
        
        self.play(graph.shift(np.array([-4, 0, 0])))

        self.pause()

        text = [
            MarkupText("Augmenting Path", font_size=32),
            MarkupText("• Path on <i>G = (V, E)</i> with respect to matching <i>M</i>", font_size=24),
            MarkupText("• Begins and ends on unmatched vertices", font_size=24),
            MarkupText("• Alternates edges in <i>M</i> and not in <i>M</i>", font_size=24),
            MarkupText("∴ Must be odd length", font_size=24),
            ]
        text[0].next_to(graph.points["E"], buff=1)
        self.play(Write(text[0]))
        ul = Underline(text[0])
        self.play(Create(ul))
        for i in range(1, len(text)):
            text[i].next_to(text[i-1], DOWN, aligned_edge=LEFT)
            
        for line in text[1:-1]:
            self.pause()
            self.play(FadeIn(line))

        self.pause()

        paths = [graph.highlight_path(*path) for path in
                 [["A", "B", "C", "F"], ["A", "B", "C", "D", "E", "F"]]]
                 
        self.play(Create(paths[0]))
        self.pause()
        self.play(FadeOut(paths[0]))
        self.pause()
        self.play(Create(paths[1]))
        self.pause()
        self.play(Circumscribe(Dot(radius=1).move_to(graph.lines[("A", "B")].get_center()), shape=Circle, color=BLUE))
        self.pause()
        self.play(Circumscribe(Dot(radius=1).move_to(graph.lines[("E", "F")].get_center()), shape=Circle, color=BLUE))
        self.pause()

        self.play(FadeIn(text[-1]))
        self.pause()
        
        # self.play(FadeOut(paths[1]))
        # self.pause()

        self.play(AnimationGroup(
            graph.apply_to_all(FadeOut),
            *[FadeOut(t) for t in text],
            FadeOut(ul)
            ))
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
        graph.draw_points(self)
        graph.draw_edges(self)

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
       
        augment = MathTex("M", "\oplus{} ", "P").next_to(graph.points["C"], direction=DOWN, buff=.5)
        self.play(FadeIn(augment))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(
            *graph.update_matching(),
            FadeOut(path_hl)
            ))
        self.pause()

        self.play(AnimationGroup(
            Indicate(augment[0]),
            Indicate(graph.lines[("B", "C")]),
            # Wiggle(graph.lines[("B", "C")]),
            Indicate(graph.lines[("D", "E")]),
            # Wiggle(graph.lines[("D", "E")]),
        ))
        self.pause()
        
        hl = Line(augment[2].get_center() + LEFT * 0.25, augment[2].get_center() + RIGHT * 0.25).set_stroke(color=YELLOW, width=48, opacity=0.5).set_z_index(-1)
        self.play(AnimationGroup(
            Create(hl),
            Create(path_hl)
            ))
        self.pause()
        self.play(FadeOut(hl))
        self.pause()
        augment2 = MathTex(r"|", r"M \oplus{} P", "| > |M|").next_to(graph.points["C"], direction=DOWN, buff=.5)
        self.play(augment.animate.move_to(augment2[1]))
        graph.invert_path(*path)
        self.play(AnimationGroup(
            FadeIn(augment2),
            FadeOut(augment),
            AnimationGroup(*graph.update_matching())
        ))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.pause()
        
        self.play(AnimationGroup(
            graph.apply_to_all(FadeOut),
            FadeOut(path_hl),
            FadeOut(augment2),
        ))
        self.pause()


class NoAPImpliesMaximum(MyScene):
    def construct(self):
        lemma = Group(
            MathTex(r"M \textrm{ is maximum}"),
            MathTex(r"\iff{}"),
            MathTex(r"\nexists \textrm{ augmenting path w.r.t } M"),
        ).arrange(RIGHT).to_edge(UP, buff=1)
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
        lines = [MathTex(s, font_size=32, substrings_to_isolate=["M'", "M", "H", r"\circ"]) for s in lines]
        for line in lines:
            line.set_color_by_tex("M", YELLOW)
            line.set_color_by_tex("M'", BLUE)
            line.set_color_by_tex("H", LIGHT_BROWN)
        proof = Group(
            *lines[:-3],
            Group(*lines[-3:]).arrange(RIGHT, buff=0.2)
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

        proof.next_to(subtitle, DOWN, buff=.5).to_edge(LEFT)
        for line in proof[:-2]:
            self.play(FadeIn(line))
            self.pause()

        graph_scale = 0.6
        def g(a):
            return Graph(a,
                solid_color=YELLOW,
                dashed_color=BLUE,
                scale=graph_scale)

        #g1 = Graph({"A": [0, 0, 0]})
        g2 = g({
            "A": [0, 0, 0],
            "B": [1, 0, 0],
            "C": [1, 1, 0],
            "D": [0, 1, 0],
        })
        g2.add_edge("A", "B")
        g2.add_edge("B", "C")
        g2.add_edge("C", "D")
        g2.add_edge("D", "A")
        g2.match("A", "B")
        g2.match("C", "D")
        
        g3 = g({
            "A": [ 0,            1,           0],
            "B": [ sin(2*pi/5),  cos(2*pi/5), 0],
            "C": [ sin(4*pi/5), -cos(  pi/5), 0],
            "D": [-sin(4*pi/5), -cos(  pi/5), 0],
            "E": [-sin(2*pi/5),  cos(2*pi/5), 0],
        })
        g3.add_edge("A", "B")
        g3.add_edge("B", "C")
        g3.add_edge("C", "D")
        g3.add_edge("D", "E")
        g3.add_edge("E", "A")
        g3.match("A", "B")
        g3.match("C", "D")
        g3.match("E", "A")

        h = 0.2
        step = sqrt(1 - h**2)
        g4 = g({
            "A": [  0,    0, 0],
            "B": [  step, h, 0],
            "C": [2*step, 0, 0],
            "D": [3*step, h, 0],
            "E": [4*step, 0, 0],
        })
        g4.add_edge("A", "B")
        g4.add_edge("B", "C")
        g4.add_edge("C", "D")
        g4.add_edge("D", "E")
        g4.match("A", "B")
        g4.match("C", "D")

        g5 = g({
            "A": [  0,    0, 0],
            "B": [  step, h, 0],
            "C": [2*step, 0, 0],
            "D": [3*step, h, 0],
            "E": [4*step, 0, 0],
            "F": [5*step, h, 0],
        })
        g5.add_edge("A", "B")
        g5.add_edge("B", "C")
        g5.add_edge("C", "D")
        g5.add_edge("D", "E")
        g5.add_edge("E", "F")
        g5.match("A", "B")
        g5.match("C", "D")
        g5.match("E", "F")

        g6 = g({
            "A": [  0,    0, 0],
            "B": [  step, h, 0],
            "C": [2*step, 0, 0],
            "D": [3*step, h, 0],
            "E": [4*step, 0, 0],
            "F": [5*step, h, 0],
        })
        g6.add_edge("A", "B")
        g6.add_edge("B", "C")
        g6.add_edge("C", "D")
        g6.add_edge("D", "E")
        g6.add_edge("E", "F")
        g6.match("B", "C")
        g6.match("D", "E")

        vstack = Group(g5.get_group(), g6.get_group()).arrange(DOWN, buff=0.5)

        group = Group(
            g2.get_group(),
            g4.get_group(),
            vstack
            ).arrange(RIGHT, buff=1)

        group.to_edge(DOWN, buff=.5)

        for g in [g2, g4, g5, g6]:
            g.draw_points(self)
            g.draw_edges(self)

        self.pause()
        
        self.play(FadeIn(proof[-2]))
        self.pause()

        g3.get_group().to_edge(RIGHT, buff=.5)
        g3.draw_points(self)
        g3.draw_edges(self)
        self.pause()
        g3.unmatch("E", "A")
        self.play(AnimationGroup(*g3.update_matching()))
        self.pause()
        g3.match("E", "A")
        self.play(AnimationGroup(*g3.update_matching()))
        self.pause()
        g3.unmatch("E", "A")
        self.play(AnimationGroup(*g3.update_matching()))
        self.pause()
        self.play(g3.apply_to_all(FadeOut))
        self.pause()

        self.play(FadeIn(proof[-1][0])),
        self.pause()

        d1 = Dot(radius=.2, fill_color=BLUE).move_to(proof[-1][1][1])
        d2 = Dot(radius=.2, fill_color=YELLOW).move_to(proof[-1][1][3])

        g6_copy = g6.get_group().copy()
        self.play(AnimationGroup(
            FadeIn(proof[-1][1]),
            FadeIn(d1),
            FadeIn(d2),
            g6_copy.animate.move_to([-5, proof[-1].get_center()[1], 0], LEFT).scale(0.4),
            ))
        self.pause()

        self.play(FadeIn(proof[-1][2])),
        self.pause()

        self.play(AnimationGroup(
            *[FadeOut(m) for m in [subtitle, proof, d1, d2]],
            g2.apply_to_all(FadeOut),
            g4.apply_to_all(FadeOut),
            g5.apply_to_all(FadeOut),
            g6.apply_to_all(FadeOut),
            FadeOut(g6_copy),
            ))
        self.play(Transform(arrow, lemma[1]))
        

class AugmentAlgorithm(MyScene):
    def construct(self):
        algo = MathTex(
            r"&\textbf{MaximumMatching}(G, M):\\",
            r"&\ \ \ \ M \leftarrow \emptyset\\",
            r"&\ \ \ \ \textbf{While } \exists \textrm{ an augmenting path } P\\",
            r"&\ \ \ \ \ \ \ \ M \leftarrow M \oplus P\\",
            r"&\ \ \ \ \textbf{return } M\\",
            ).to_edge(LEFT, buff=.5)
            
        self.play(FadeIn(algo))
        self.pause()
        
        halts = MathTex(r"\nexists P \Rightarrow M \textrm{ is maximum}", color=YELLOW)
        halts.next_to(algo.get_part_by_tex(r"augmenting path"), RIGHT, buff=.5)

        monotonic = MathTex(r"|M \oplus P| > |M|", color=YELLOW)
        monotonic.next_to(algo.get_part_by_tex(r"M \oplus P"), RIGHT, buff=.5)
        
        self.play(FadeIn(monotonic))
        self.pause()
        self.play(FadeIn(halts))
        self.pause()

        self.play(AnimationGroup(
            FadeOut(halts),
            FadeOut(monotonic),
        ))
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
        graph.draw_points(self)
        graph.draw_edges(self)
        self.pause()
        self.play(graph.shift([-3, 0, 0]))
        self.pause()

        algo = VGroup(*[Tex(x, font_size=32) for x in [
            r"Select an unmatched vertex $v$",
            r"Perform a DFS from $v$",
            r"Keep track of the distance travelled",
            r"— Every odd step, take an edge $\notin M$",
            r"— Every even step, take an edge $\in M$",
            r"If you ever find an unmatched vertex at an",
            r"odd distance, you have an augmenting path",
            ]]).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        algo.to_edge(RIGHT, buff=.5)
        
        self.play(FadeIn(algo[0]))
        self.play(AnimationGroup(
            FocusOn(graph.points["C"].get_center()),
            graph.points["C"].animate.set_fill(YELLOW)
            ))
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
        self.play(AnimationGroup(
            Create(p2),
            Transform(count, Text("2", color=YELLOW).next_to(graph.points["E"], UP+RIGHT))
            ))
        self.pause()
        
        p3 = graph.highlight_path("E", "F")
        self.play(AnimationGroup(
            Create(p3),
            Transform(count, Text("3", color=YELLOW).next_to(graph.points["F"], RIGHT))
            ))
        self.pause()
        
        self.play(AnimationGroup(
            FadeIn(algo[5]),
            FadeIn(algo[6])
            ))
        self.pause()

        graph.invert_path("C", "D", "E", "F")
        
        self.play(AnimationGroup(
            FadeOut(count),
            graph.points["C"].animate.set_fill(WHITE),
            *graph.update_matching()
            ))
        self.pause()
        
        self.play(AnimationGroup(
            *(FadeOut(p) for p in [p1, p2, p3])
            ))
        self.pause()

        graph.unmatch("A", "B")
        graph.unmatch("C", "D")
        graph.unmatch("E", "F")

        self.play(AnimationGroup(
            FadeOut(algo),
            graph.shift([3, 0, 0]),
            ))
        self.play(AnimationGroup(
            *graph.update_matching()
            ))
        self.pause()

        
class AugmentAlgorithmCounterexample(MyScene):
    def construct(self):
        graph = Graph({
            "A": [-2 * sin(2*pi/5),    2 * cos(2*pi/5), 0],
            "B": [ 0,                  2,               0],
            "C": [ 2 * sin(2*pi/5),    2 * cos(2*pi/5), 0],
            "D": [ 2 * sin(4*pi/5),   -2 * cos(  pi/5), 0],
            "E": [-2 * sin(4*pi/5),   -2 * cos(  pi/5), 0],
            "F": [-2 * sin(4*pi/5)-2, -2 * cos(  pi/5), 0],
        })
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "A")
        graph.add_edge("E", "F")
        graph.match("B", "C")
        graph.match("D", "E")
        graph.draw_points(self)
        graph.draw_edges(self)
        self.pause()
        p1_points = [ "A", "B", "C", "D", "E", "F" ]
        p1 = [graph.highlight_path(p1_points[i], p1_points[i + 1]) for i in range(5)]
        directions = {
            "A": UP + LEFT,
            "B": UP,
            "C": UP+RIGHT,
            "D": DOWN+RIGHT,
            "E": DOWN,
            "F": DOWN
        }
        count = Text("0", color=YELLOW).next_to(graph.points["A"], directions["A"])
        self.play(AnimationGroup(
            FocusOn(graph.points["A"].get_center()),
            graph.points["A"].animate.set_fill(YELLOW)
            ))
        self.play(Write(count))
        self.pause()
        for i, p in enumerate(p1):
            move_to = p1_points[i + 1]
            self.play(AnimationGroup(
                Create(p),
                Transform(count,
                    Text(str(i+1),
                        color=YELLOW
                        ).next_to(graph.points[move_to],
                            directions[move_to]))
                ))
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
        self.play(AnimationGroup(
            *[FadeOut(p) for p in p1],
            FadeIn(p1_solid),
            FadeOut(count)
            ))
        self.play(Uncreate(p1_solid))

        count = Text("1", color=YELLOW).next_to(graph.points["E"], directions["E"])

        p2 = graph.highlight_path("A", "E")
        self.play(AnimationGroup(
            Create(p2),
            Write(count),
            ))
        self.pause()
        p3 = graph.highlight_path("E", "F")
        self.play(Create(p3))
        self.play(Uncreate(p3))
        self.pause()
        
        p3 = graph.highlight_path("E", "D", "C", "B")
        self.play(AnimationGroup(
            Create(p3),
            Transform(count, Text("4", color=YELLOW).next_to(graph.points["B"], DOWN)),
            ))
        self.pause()

        self.play(AnimationGroup(
            FadeOut(p2),
            FadeOut(p3),
            FadeOut(count),
        ))
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
        dy = sqrt(4 - dx ** 2)
        self.play(graph.rearrange({
            "A": [x+dx, y-0*dy, 0],
            "B": [x   , y-1*dy, 0],
            "C": [x+dx, y-2*dy, 0],
            "D": [x   , y-2*dy, 0],
            "E": [x+dx, y-3.5*dy, 0],
            "F": [x   , y-3.5*dy, 0],
        }))
        self.pause()

        self.play(
            graph.rearrange({
                "A": ORIGIN,
                "B": ORIGIN,
                "C": ORIGIN,
                "D": ORIGIN,
                "E": ORIGIN,
                "F": ORIGIN,
            })
        )
        self.play(FadeOut(graph.get_group()))
        self.pause()

        text = VGroup(*[Tex(x) for x in [
            r"Augmenting path matching on a bipartite graph $G=(V, E)$\\",
            r"|V|=n, |E|=m\\",
            r"$n/2$ searches\\",
            r"Each DFS is $O(m)$\\",
            r"$O(nm)$\\",
            r"$O(m\sqrt{n})$\\",
        ]]).arrange(DOWN, buff=.3)
        for line in text:
            self.play(FadeIn(line))
            self.pause()
        self.play(FadeOut(text))
        self.pause()


class BlossomDefinition(MyScene):
    def construct(self):
        graph_points = {
            "A": np.array([-2,                0,               0]),
            "B": np.array([-2 * cos(2*pi/5),  2 * sin(2*pi/5), 0]),
            "C": np.array([ 2 * cos(  pi/5),  2 * sin(4*pi/5), 0]),
            "D": np.array([ 2 * cos(  pi/5), -2 * sin(4*pi/5), 0]),
            "E": np.array([-2 * cos(2*pi/5), -2 * sin(2*pi/5), 0]),
            "F": np.array([-4              ,  0              , 0]),
            "G": np.array([-6              ,  0              , 0]),
            "H": np.array([-6              , -2              , 0]),
            "I": np.array([-4              , -2              , 0]),
        }
        shift = RIGHT * 3 + DOWN * .5
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

        definition = VGroup(*[Tex(x) for x in [
            r"$\bullet$ Cycle of size $2k+1$\\",
            r"$\bullet$ $k$ internally matched edges\\",
            r"$\bullet$ A stem"
            ]]).arrange(DOWN, aligned_edge=LEFT).next_to(blossom, DOWN, buff=.75).to_edge(LEFT)
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
        self.play(LaggedStart(
            Indicate(l1),
            Indicate(l2),
            lag_ratio=0.2
        ))
        self.pause()

        self.play(FadeOut(k_2))
        self.pause()

        ee = ((graph_points["E"] - shift) * 1.4) + shift
        graph.add_point("ee", ee, hidden=True)
        graph.add_edge("ee", "E")
        self.play(FadeIn(graph.lines[("E", "ee")]))
        self.pause()

        arc_margin = 2*PI/40
        arc_a = Arc(start_angle=PI - arc_margin, angle=2*arc_margin - (4 * 2*PI / 5), radius=2.5, stroke_color=YELLOW).shift(shift)
        arc_b = Arc(start_angle=PI + arc_margin, angle=-2*arc_margin + (1 * 2*PI / 5), radius=2.5, stroke_color=YELLOW).shift(shift)
        aa = ((graph_points["A"] - shift) * 1.4) + shift
        ee_line = graph.lines[("E", "ee")]
        out_delta_a = arc_a.get_end() - ee_line.get_start()
        out_line_a = Arrow(
            ee_line.get_start() + out_delta_a,
            ee_line.get_end() + out_delta_a,
            max_stroke_width_to_length_ratio=999,
            max_tip_length_to_length_ratio=.3,
            buff=0, color=YELLOW)
        in_delta_a = arc_a.get_start() - graph_points["A"]
        in_line_a = Line(aa + in_delta_a, graph_points["A"] + in_delta_a).set_stroke(color=YELLOW)

        out_delta_b = arc_b.get_end() - ee_line.get_start()
        out_line_b = Arrow(
            ee_line.get_start() + out_delta_b,
            ee_line.get_end() + out_delta_b,
            max_stroke_width_to_length_ratio=999,
            max_tip_length_to_length_ratio=.3,
            buff=0, color=YELLOW)
        in_delta_b = arc_b.get_start() - graph_points["A"]
        in_line_b = Line(aa + in_delta_b, graph_points["A"] + in_delta_b, color=YELLOW)
        
        self.play(LaggedStart(
            Create(VGroup(in_line_a, arc_a, out_line_a)),
            Create(VGroup(in_line_b, arc_b, out_line_b)),
            lag_ratio=.3
        ))
        self.pause()
        
        self.play(AnimationGroup(
            FadeOut(VGroup(in_line_a, arc_a, out_line_a)),
            FadeOut(VGroup(in_line_b, arc_b, out_line_b)),
        ))
        self.pause()

        a = graph_points["A"]
        b = graph_points["B"]
        e = graph_points["E"]
        ab = b - a
        ae = e - a
        choice_a = Arrow(a - .2 * ae, a - .2 * ae + .6 * ab, max_tip_length_to_length_ratio=.3, max_stroke_width_to_length_ratio=5, color=YELLOW, stroke_width=5, buff=.1)
        choice_b = Arrow(a - .2 * ab, a - .2 * ab + .6 * ae, max_tip_length_to_length_ratio=.3, max_stroke_width_to_length_ratio=5, color=YELLOW, stroke_width=5, buff=.1)
        self.play(LaggedStart(
            LaggedStart(
                FocusOn(graph.points["A"]),
                graph.points["A"].animate.set_fill(color=YELLOW),
                lag_ratio=.4
            ),
            LaggedStart(
                GrowArrow(choice_a),
                GrowArrow(choice_b),
                lag_ratio=.2
            ),
            lag_ratio=0.6
            ))
        self.pause()

        graph.points["A"].set_z_index(9999)
        
        root = Tex("root", color=YELLOW)
        root.next_to(graph.points["A"], RIGHT, buff=0.4)
        self.play(Write(root))
        self.pause()

        self.play(AnimationGroup(
            FadeOut(choice_a),
            FadeOut(choice_b),
        ))
        self.pause()
        
        graph.match("A", "F")
        graph.update_matching(animated=False)
        self.play(LaggedStart(
            GrowFromPoint(graph.lines[("A", "F")], graph_points["A"]),
            GrowFromCenter(graph.points["F"]),
            lag_ratio=.3
            ))
        self.pause()

        self.play(Indicate(graph.points["A"]))
        self.pause()

        self.play(AnimationGroup(
            FadeOut(graph.lines[("A", "F")]),
            FadeOut(graph.points["F"]),
            FadeOut(graph.lines[("E", "ee")])
        ))
        self.pause()

        stem_text = Tex("stem", color=BLUE).next_to(graph_points["F"], UP, buff=.4)
        self.play(LaggedStart(
            GrowFromPoint(graph.lines[("A", "F")], graph_points["A"]),
            GrowFromCenter(graph.points["F"]),
            GrowFromPoint(graph.lines[("F", "G")], graph_points["F"]),
            GrowFromCenter(graph.points["G"]),
            Write(stem_text),
            lag_ratio=.3
            ))
        self.pause()

        stem_hl = graph.highlight_path("A", "F", "G").set_stroke(color=BLUE)
        self.play(ShowPassingFlash(stem_hl, time_width=1, time=1.5))
        self.pause()

        stem_text_copy = stem_text.copy()
        self.play(Transform(stem_text_copy, definition[2]))
        self.pause()

        graph.match("G", "H")
        graph.update_matching(animated=False)
        self.play(AnimationGroup(
            FadeIn(graph.get_sub_group(["H", "I"])),
            FadeIn(graph.lines[("G", "H")]),
        ))
        self.pause()
        self.play(AnimationGroup(
            FadeOut(graph.get_sub_group(["F", "G", "H", "I"])),
            FadeOut(graph.lines[("A", "F")]),
            FadeOut(stem_text)
        ))
        self.pause()
        self.play(AnimationGroup(
            FadeIn(graph.points["F"]),
            FadeIn(graph.lines[("A", "F")]),
        ))
        self.pause()
        self.play(AnimationGroup(
            FadeOut(graph.points["F"]),
            FadeOut(graph.lines[("A", "F")]),
            graph.points["A"].animate.set_fill(color=WHITE)
        ))
        self.pause()
        self.play(AnimationGroup(
            FadeOut(blossom),
            FadeOut(definition),
            FadeOut(stem_text_copy),
            FadeOut(root),
            graph.get_sub_group(["A", "B", "C", "D", "E"]).animate.shift(-shift)
        ))
        self.pause()


class BlossomShrinkingProof(MyScene):
    def construct(self):
        graph_points = {
            "A": np.array([-2 * sin(2*pi/5),    2 * cos(2*pi/5), 0]),
            "B": np.array([ 0,                  2,               0]),
            "C": np.array([ 2 * sin(2*pi/5),    2 * cos(2*pi/5), 0]),
            "D": np.array([ 2 * sin(4*pi/5),   -2 * cos(  pi/5), 0]),
            "E": np.array([-2 * sin(4*pi/5),   -2 * cos(  pi/5), 0]),
            # "F": np.array([-2 * sin(4*pi/5)-2, -2 * cos(  pi/5), 0]),
        }
        graph = Graph(graph_points)
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "A")
        graph.match("B", "C")
        graph.match("D", "E")
        graph.make_edges()
        g = graph.get_group()
        # self.play(FadeIn(g))

        proof_lines = [
            (0, r"Contract blossom $B \rightarrow$ vertex $B'$ to transform $M \rightarrow M'$ ($|M|>|M'|$)"),
            (0, r"$M'$ is maximum $\implies{}$ $M$ is maximum"),
            (0, r"By contradiction: assume $M'$ is maximum but $M$ isn't."),
            (0, r"$\implies{}$ There must be some augmenting path $P$ w.r.t. $M$"),
            (0, r"3 cases:"),
            (1, r"1. $P$ doesn't intersect $B$"),
            (2, r"$P$ must also exist in $M'$. $M'$ is not maximum"),
            (1, r"2. $P$ has an endpoint in $B$"),
            (2, r"A.P. must end on an unmatched vertex"),
            (2, r"A blossom has either $0$ or $1$ unmatched vertices"),
            (2, r"If $P$ ends in $B$, $B$ has 1 unmatched vertex"),
            (2, r"Let $(u,v) \in P : u \in B, v \not\in B$"),
            (2, r"$(u,v)$ must be unmatched ($\nexists$ matches $B \leftrightarrow  M$)"),
            (2, r"Construct A.P. w.r.t $M'$ with all of $P$ up to $v$, plus $(v, B’)$"),
            (2, r"$M'$ is not maximum"),
            (1, r"3. $P$ passes through $B$"),
            (2, r"Let $(u_1, v_1), (u_2, v_2) \in P : u_1, u_2 \in B, v_1, v_2 \not\in B$"),
            (2, r"3 cases:"),
            (3, r"$1$. $(u_1, v_1), (u_2, v_2) \in M$"),
            (4, r"Not possible ($B$ has $\le1$ unmatched vertex)"),
            (3, r"$2$. $(u_1, v_1) \in M, (u_2, v_2) \not\in M$"),
            (4, r"Create an A.P. w.r.t. M' by contracting $u_1 = u_2 = B'$"),
            (4, r"New path is $(P\textrm{ up to }v_1) \rightarrow v_1 \rightarrow B' \rightarrow v_2 \rightarrow (P\textrm{ from }v_2)$"),
            (3, r"$1$. $(u_1, v_1), (u_2, v_2) \not\in M$"),
            (4, r"If the root of $B$ is unmatched"),
            (5, r"Then $B'$ is unmatched"),
            (5, r"Construct a new A.P. with $(P\textrm{ up to }v_1) \rightarrow v_1 \rightarrow B'$"),
            (4, r"If the root of $B$ is matched"),
            (5, r"$B'$ is matched with the stem of $P$ (which must end in an unmatched vertex)"),
            (5, r"Construct a new A.P. with $(P\textrm{ up to }v_1) \rightarrow v_1 \rightarrow B' \rightarrow \textrm{stem}(B)$"),
        ]

        proof = VGroup(*[Tex(tex, font_size=12) for (_, tex) in proof_lines]).arrange(DOWN, aligned_edge=LEFT).to_edge(DOWN)
        for i, (offset, _) in enumerate(proof_lines):
            proof[i].shift([offset/2, 0, 0])
        
        self.add(proof)
        # self.wait()

        # for x in proof:
        #     self.play(Write(x))
        #     self.pause()


class LinearProgrammingIntro(Slide):
    def construct(self):
        optimize = Tex("Optimize:")
        function = MathTex(r"f(x,y)=180x+200y")
        subject_to = Tex("Subject to constraints:")
        constraint_tex = MathTex(
            r"5x+4y & \le 80\\",
            r"10x+20y & \le 200\\",
            r"x & \ge 0\\",
            r"y & \ge 0\\",
        )
        spacer = Rectangle(width=0, height=.5).set_stroke(color=None, width=0).set_fill(color=None)
        g = VGroup(optimize, function, spacer, subject_to, constraint_tex).arrange(DOWN, buff=.3)
        optimize.shift(LEFT * 3)
        subject_to.align_to(optimize, LEFT)
        self.play(AnimationGroup(
            FadeIn(optimize),
            FadeIn(function),
        ))
        self.pause()
        self.play(Transform(
            optimize, Tex("Maximize:").move_to(optimize, aligned_edge=LEFT)
        ))
        self.pause()
        self.play(LaggedStart(
            FadeIn(subject_to),
            *[FadeIn(x) for x in constraint_tex],
            lag_ratio=.6
        ))
        self.pause()
        self.play(FadeOut(g))
        self.pause()

        title = Tex("Carpenter maximizing proffit")
        bullets = BulletedList(
            r"Tables take 10 units of lumber, 5 hours of labor. Make \$180 proffit",
            r"Bookshelves take 20 units of lumber, 4 hours of labor. Make \$200 proffit",
            r"200 units of lumber available",
            r"80 hours of labor available",
            width=4
            )
        
        word_problem = VGroup(title, bullets).arrange(DOWN, aligned_edge=LEFT)
        self.play(FadeIn(title))
        self.pause()
        for line in bullets:
            self.play(FadeIn(line))
            self.pause()
        



class Presentation2(Slide):
    def construct(self):
        slides = [
            StableMatching,
            StableVsMaximumTable,
            MaximumMatchingIntro,
            FourProblems,
            AugmentingPath,
            MaximumImpliesNoAP,
            NoAPImpliesMaximum,
            AugmentAlgorithm,
            AugmentAlgorithmExample,
            AugmentAlgorithmCounterexample,
            BipartiteAnimation,
            Blossom
        ]

        for s in slides:
            s.construct(self)
            self.clear()
            self.pause()
