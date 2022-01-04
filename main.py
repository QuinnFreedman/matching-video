from manim import *
from manim.mobject.opengl_compatibility import ConvertToOpenGL
from typing import Callable, Iterable, Optional, Sequence
from math import sin, cos, pi, sqrt


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
        return Group(
            *self.points.values(),
            *self.lines.values(),
        )
        
    def get_sub_group(self, vertices):
        points = [self.points[v] for v in vertices]
        edges = [self.lines[e] for e in self.edges if e[0] in vertices and e[1] in vertices]
        return Group(*points, *edges)

    def draw_points(self, scene):
        scene.add(*self.points.values())

    def apply_to_all(self, animation):
        return AnimationGroup(
            *[animation(p) for p in self.points.values()],
            *[animation(l) for l in self.lines.values()]
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
        self.edges.add(tuple(sorted((p1, p2))))

    def UnconnectedEdge(self, p1, p2):
            return DashedLine(p1, p2, stroke_width=10*self.scale, dash_length=0.1*self.scale, dashed_ratio=0.4, stroke_color=self.dashed_color)
            
    def ConnectedEdge(self, p1, p2):
            return Line(p1, p2, stroke_width=10*self.scale, stroke_color=self.solid_color)

    def _make_edge(self, edge):
        p1 = self.points[edge[0]]
        p2 = self.points[edge[1]]
        if edge in self.matching:
            return self.ConnectedEdge(p1, p2)
        else:
            return self.UnconnectedEdge(p1, p2)

    def draw_edges(self, scene):
        self.lines = {}
        for edge in self.edges:
            line = self._make_edge(edge)
            self.lines[edge] = line
            scene.add(line)

    def match(self, p1, p2):
        self.matching.add(tuple(sorted((p1, p2))))
        
    def unmatch(self, p1, p2):
        self.matching.remove(tuple(sorted((p1, p2))))

    def update_matching(self):
        animations = []
        for edge in self.edges:
            old_line = self.lines[edge]
            self._make_edge(edge)
            new_line = self._make_edge(edge)
            if old_line.__class__.__name__ != new_line.__class__.__name__:
                self.lines[edge] = new_line
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

        return animations

    def rearange(self, new_points):
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


class StableMatching(Scene):
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
        self.wait(.25)
        self.play(Circumscribe(VGroup(*text[0]), time_width=0.5, buff=0.2))
        self.wait(.25)
        self.play(Circumscribe(VGroup(*text[1]), time_width=0.5, buff=0.2))
        self.wait(.25)

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
        self.wait(.25)
        self.play(LaggedStart(
            *[FadeOut(a) for a in matching1],
            lag_ratio=0.15
        ))
        self.wait(.25)

        matching2 = [
            edge((0,0), (1,0)),
            edge((0,1), (1,1)),
            edge((0,2), (1,2)),
        ]

        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching2],
            lag_ratio=0.25
        ))
        self.wait(.25)
        self.play(LaggedStart(
            *[FadeOut(a) for a in matching2],
            lag_ratio=0.15
        ))
        self.wait(.25)

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
        self.wait(.25)
        self.play(Write(popup_text[1]))
        self.wait(.25)

        self.play(LaggedStart(
            FadeOut(popup_text[0]),
            popup_text[1].animate.move_to([
                popup_text[1].get_center()[0],
                popup_text[0].get_center()[1],
                0
            ])
        ))
        self.wait(.25)

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
        self.wait(.25)
        self.play(Indicate(popup_text_2[0]))
        self.wait(.25)

        self.play(AnimationGroup(
            hide,
            FadeOut(popup_text_2)
            ))
        self.wait(.25)

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
        self.wait(.25)

        self.play(LaggedStart(
            *[Create(prefs) for prefs in pref_squares[1:3]],
            *[Write(x) for pref_group in prefs_mtext[1:3] for x in pref_group],
            lag_ratio=0.3
        ))
        self.wait(.25)

        self.play(LaggedStart(
            *[Create(prefs) for prefs in pref_squares[3:]],
            *[Write(x) for pref_group in prefs_mtext[3:] for x in pref_group],
            lag_ratio=0.3
        ))
        self.wait(.25)

        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][0]),
            IndicateEdges(pref_squares[0][0], scale_factor=1.5),
        ))
        self.wait(.25)
        self.play(AnimationGroup(
            Indicate(prefs_mtext[3][1]),
            IndicateEdges(pref_squares[3][1], scale_factor=1.5),
        ))
        self.wait(.25)

        # matte_stack = [
        #     Rectangle(width=10,  height=10).set_fill(color=BLACK, opacity=0.5).set_stroke(width=0),
        #     Rectangle(width=6, height=2).set_fill(color=BLACK, opacity=1).set_stroke(color=WHITE)
        # ]
        # stable_matching_text = Text("Stable Matching", slant=ITALIC).move_to([0,0,0])
        # self.play(LaggedStart(
        #     FadeIn(VGroup(*matte_stack)),
        #     Write(stable_matching_text)
        # ))
        # self.wait(.25)

        # self.play(AnimationGroup(
        #     FadeOut(VGroup(*matte_stack)),
        #     FadeOut(stable_matching_text),
        # ))
        # self.wait(.25)

        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching1],
            lag_ratio=0.25
        ))
        self.wait(.25)

        self.play(LaggedStart(
            Indicate(text[0][0]),
            Indicate(text[1][0]),
            lag_ratio=0.8
        ))
        self.wait(.25)
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][1]),
            Indicate(prefs_mtext[3][2]),
            IndicateEdges(pref_squares[0][1], scale_factor=1.5),
            IndicateEdges(pref_squares[3][2], scale_factor=1.5),
            Indicate(matching1[0]),
            Indicate(matching1[2]),
        ))
        self.wait(.25)
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][0]),
            Indicate(prefs_mtext[3][1]),
            IndicateEdges(pref_squares[0][0], scale_factor=1.5),
            IndicateEdges(pref_squares[3][1], scale_factor=1.5),
        ))
        self.wait(.25)

        matching1[0].set_z_index(-1)
        matching1[2].set_z_index(-1)
        self.play(AnimationGroup(
            matching1[0].animate.set_stroke(color=GRAY_E).set_fill(color=GRAY_E),
            matching1[2].animate.set_stroke(color=GRAY_E).set_fill(color=GRAY_E),
        ))
        self.wait(.25)

        self.play(Circumscribe(
            VGroup(text[0][0], text[1][0], *prefs_mtext[0], *prefs_mtext[3])
        ))
        self.wait(.25)

        extra_edge = edge((0,0), (1,0))
        self.play(GrowArrow(extra_edge))
        self.wait(.25)
        
        self.play(AnimationGroup(
            Indicate(text[0][2]),
            Indicate(text[1][1])
        ))
        self.wait(.25)

        self.play(AnimationGroup(
            *[FadeOut(a) for a in matching1],
            FadeOut(extra_edge)
        ))
        self.wait(.25)

        matching3 = [
            edge((0,0), (1,1)),
            edge((0,1), (1,0)),
            edge((0,2), (1,2)),
        ]
        self.play(LaggedStart(
            *[GrowArrow(a) for a in matching3],
            lag_ratio=0.25
        ))
        self.wait(.25)
        
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][1]),
            IndicateEdges(pref_squares[0][1], scale_factor=1.5),
            Indicate(matching3[0])
        ))
        self.wait(.25)
        self.play(AnimationGroup(
            Indicate(prefs_mtext[0][0]),
            IndicateEdges(pref_squares[0][0], scale_factor=1.5),
        ))
        self.wait(.25)
        self.play(AnimationGroup(
            Indicate(prefs_mtext[3][0]),
            IndicateEdges(pref_squares[3][0], scale_factor=1.5),
            Indicate(matching3[1])
        ))
        self.wait(.25)
        self.play(AnimationGroup(
            *(FadeOut(x) for y in prefs_mtext for x in y),
            *(FadeOut(x) for x in pref_squares),
            *(FadeOut(x) for x in matching3)
        ))
        self.wait(.25)


class MaximumMatchingIntro(Scene):
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
        self.wait(.25)

        def dashed_line(p1, p2):
            return DashedLine(p1, p2, stroke_width=10, dash_length=0.1, dashed_ratio=0.4, buff=.5, stroke_color=GRAY_D)
            
        def solid_line(p1, p2):
            return Line(p1, p2, stroke_width=10, buff=.5, z_index=10)

        edges = [
            dashed_line(text[0][0].get_center(), text[1][0].get_center()),
            dashed_line(text[0][0].get_center(), text[1][1].get_center()),
            dashed_line(text[0][1].get_center(), text[1][1].get_center()),
            dashed_line(text[0][1].get_center(), text[1][2].get_center()),
            dashed_line(text[0][2].get_center(), text[1][1].get_center()),
        ]
        self.play(AnimationGroup(
            *(FadeIn(e) for e in edges)
        ))
        self.wait(.25)

        l1 = solid_line(text[0][0].get_center(), text[1][0].get_center())
        l2 = solid_line(text[0][1].get_center(), text[1][1].get_center())
        self.play(AnimationGroup(
            GrowFromCenter(l1),
            FadeOut(edges[0]),
        ))
        self.wait(.25)

        self.play(AnimationGroup(
            GrowFromCenter(l2),
            FadeOut(edges[2]),
        ))
        self.wait(.25)

        self.play(Indicate(text[0][2]))
        self.wait(.25)

        self.play(AnimationGroup(
            ShrinkToCenter(l1),
            ShrinkToCenter(l2),
            FadeIn(edges[0]),
            FadeIn(edges[2]),
        ))
        self.wait(.25)
        
        l1 = solid_line(text[0][0].get_center(), text[1][0].get_center())
        l3 = solid_line(text[0][1].get_center(), text[1][2].get_center())
        l4 = solid_line(text[0][2].get_center(), text[1][1].get_center())
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
        self.wait(.25)

        self.play(AnimationGroup(
            FadeOut(l1),
            FadeOut(l3),
            FadeOut(l4),
            FadeIn(edges[0]),
            FadeIn(edges[3]),
            FadeIn(edges[4]),
        ))
        self.wait(.25)


class AugmentingPath(Scene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.draw_points(self)
        graph.draw_edges(self)

        self.wait(1)

        graph.match("B", "C")
        graph.match("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)
        
        graph.unmatch("B", "C")
        graph.unmatch("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)
        
        graph.match("A", "B")
        graph.match("C", "D")
        graph.match("E", "F")
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)
        
        graph.unmatch("A", "B")
        graph.unmatch("C", "D")
        graph.unmatch("E", "F")
        self.play(AnimationGroup(*graph.update_matching()))
        graph.match("B", "C")
        graph.match("D", "E")
        self.play(AnimationGroup(*graph.update_matching()))
        
        self.wait(.25)
        
        self.play(graph.shift(np.array([-4, 0, 0])))

        self.wait(1)

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
            self.wait(.25)
            self.play(FadeIn(text[i]))

        
        self.wait(1)

        for path in [["A", "B", "C", "F"], ["A", "B", "C", "D", "E", "F"]]:
            path_hl = graph.highlight_path(*path)
            self.play(Create(path_hl))
            self.wait(1)
            self.play(FadeOut(path_hl))
            self.wait(1)

        self.wait(1)

        self.play(AnimationGroup(
            graph.apply_to_all(FadeOut),
            *[FadeOut(t) for t in text],
            FadeOut(ul)
            ))
        self.wait(.25)


class MaximumImpliesNoAP(Scene):
    def construct(self):
        lemma = Group(
            MathTex(r"M \textrm{ is maximum}"),
            MathTex(r"\iff{}"),
            MathTex(r"\nexists \textrm{ augmenting path w.r.t } M"),
        ).arrange(RIGHT)
        self.play(FadeIn(lemma))
        self.wait(.25)
        
        self.play(Transform(lemma[1], MathTex(r"\Longrightarrow{}").move_to(lemma[1])))

        self.wait(.25)
        
        self.play(lemma.animate.to_edge(UP, buff=1))
        self.wait(.25)

        graph = _make_even_cycle_graph()
        graph.match("B", "C")
        graph.match("D", "E")
        graph.draw_points(self)
        graph.draw_edges(self)

        path = ["A", "B", "C", "F"]
        
        path_hl = graph.highlight_path(*path)
        self.play(Create(path_hl))
        self.wait(.25)
        
        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)
       
        augment = MathTex("M", "\oplus{} ", "P").next_to(graph.points["C"], direction=DOWN, buff=.5)
        self.play(FadeIn(augment))
        self.wait(.25)

        graph.invert_path(*path)
        self.play(AnimationGroup(
            *graph.update_matching(),
            FadeOut(path_hl)
            ))
        self.wait(.25)

        self.play(AnimationGroup(
            Indicate(augment[0]),
            Indicate(graph.lines[("B", "C")]),
            # Wiggle(graph.lines[("B", "C")]),
            Indicate(graph.lines[("D", "E")]),
            # Wiggle(graph.lines[("D", "E")]),
        ))
        self.wait(.25)
        
        hl = Line(augment[2].get_center() + LEFT * 0.25, augment[2].get_center() + RIGHT * 0.25).set_stroke(color=YELLOW, width=48, opacity=0.5).set_z_index(-1)
        self.play(AnimationGroup(
            Create(hl),
            Create(path_hl)
            ))
        self.wait(.25)
        self.play(FadeOut(hl))
        self.wait(.25)
        augment2 = MathTex(r"|", r"M \oplus{} P", "| > |M|").next_to(graph.points["C"], direction=DOWN, buff=.5)
        self.play(augment.animate.move_to(augment2[1]))
        graph.invert_path(*path)
        self.play(AnimationGroup(
            FadeIn(augment2),
            FadeOut(augment),
            AnimationGroup(*graph.update_matching())
        ))
        self.wait(.25)

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)

        graph.invert_path(*path)
        self.play(AnimationGroup(*graph.update_matching()))
        self.wait(.25)
        
        self.play(AnimationGroup(
            graph.apply_to_all(FadeOut),
            FadeOut(path_hl),
            FadeOut(augment2),
        ))
        self.wait(.25)


class NoAPImpliesMaximum(Scene):
    def construct(self):
        lemma = Group(
            MathTex(r"M \textrm{ is maximum}"),
            MathTex(r"\iff{}"),
            MathTex(r"\nexists \textrm{ augmenting path w.r.t } M"),
        ).arrange(RIGHT).to_edge(UP, buff=1)
        arrow = MathTex(r"\Longrightarrow{}").move_to(lemma[1])

        self.add(lemma[0], lemma[2], arrow)
        self.play(Rotate(arrow))
        self.wait(.25)

        subtitle = Tex(
            r"By contrapositive: $M$ is not maximum $\Longrightarrow{} M$ has an augmenting path",
            font_size=32,
            ).next_to(lemma, DOWN)
        self.play(FadeIn(subtitle))
        self.wait(.25)

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
            self.wait(.25)

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

        self.wait(.25)
        
        self.play(FadeIn(proof[-2]))
        self.wait(.25)

        g3.get_group().to_edge(RIGHT, buff=.5)
        g3.draw_points(self)
        g3.draw_edges(self)
        self.wait(.25)
        g3.unmatch("E", "A")
        self.play(AnimationGroup(*g3.update_matching()))
        self.wait(.25)
        g3.match("E", "A")
        self.play(AnimationGroup(*g3.update_matching()))
        self.wait(.25)
        g3.unmatch("E", "A")
        self.play(AnimationGroup(*g3.update_matching()))
        self.wait(.25)
        self.play(g3.apply_to_all(FadeOut))
        self.wait(.25)

        self.play(FadeIn(proof[-1][0])),
        self.wait(.25)

        d1 = Dot(radius=.2, fill_color=BLUE).move_to(proof[-1][1][1])
        d2 = Dot(radius=.2, fill_color=YELLOW).move_to(proof[-1][1][3])

        g6_copy = g6.get_group().copy()
        self.play(AnimationGroup(
            FadeIn(proof[-1][1]),
            FadeIn(d1),
            FadeIn(d2),
            g6_copy.animate.move_to([-5, proof[-1].get_center()[1], 0], LEFT).scale(0.4),
            ))
        self.wait(.25)

        self.play(FadeIn(proof[-1][2])),
        self.wait(.25)

        self.play(AnimationGroup(
            *[FadeOut(m) for m in [subtitle, proof, d1, d2]],
            *g2.apply_to_all(FadeOut),
            *g4.apply_to_all(FadeOut),
            *g5.apply_to_all(FadeOut),
            *g6.apply_to_all(FadeOut),
            ))
        self.play(Transform(lemma[1], MathTex(r"\iff{}")))
        

class AugmentAlgorithm(Scene):
    def construct(self):
        algo = MathTex(
            r"&\textbf{MaximumMatching}(G, M):\\",
            r"&\ \ \ \ M \leftarrow \emptyset\\",
            r"&\ \ \ \ \textbf{While } \exists \textrm{ an augmenting path } P\\",
            r"&\ \ \ \ \ \ \ \ M \leftarrow M \oplus P\\",
            r"&\ \ \ \ \textbf{return } M\\",
            ).to_edge(LEFT, buff=.5)
            
        self.play(FadeIn(algo))
        self.wait(.25)
        
        halts = MathTex(r"\nexists P \Rightarrow M \textrm{ is maximum}", color=YELLOW)
        halts.next_to(algo.get_part_by_tex(r"augmenting path"), RIGHT, buff=.5)

        monotonic = MathTex(r"|M \oplus P| > |M|", color=YELLOW)
        monotonic.next_to(algo.get_part_by_tex(r"M \oplus P"), RIGHT, buff=.5)
        
        self.play(FadeIn(monotonic))
        self.wait(.25)
        self.play(FadeIn(halts))
        self.wait(.25)

        self.play(AnimationGroup(
            FadeOut(halts),
            FadeOut(monotonic),
        ))
        self.wait(.25)

        self.play(Indicate(algo.get_part_by_tex("While")))
        self.wait(.25)
        self.play(FadeOut(algo))
        self.wait(.25)
        
class AugmentAlgorithmExample(Scene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.match("A", "B")
        graph.match("D", "E")
        graph.draw_points(self)
        graph.draw_edges(self)
        self.wait(.25)
        self.play(graph.shift([-3, 0, 0]))
        self.wait(.25)

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
        self.wait(.25)

        self.play(FadeIn(algo[1]))
        self.wait(.25)

        dfs = graph.highlight_path("C", "B", "A")
        self.play(Create(dfs))
        self.play(Uncreate(dfs))
        dfs = graph.highlight_path("C", "D", "E", "F", "C")
        self.play(Create(dfs))
        self.play(Uncreate(dfs))
        self.wait(.25)

        p1 = graph.highlight_path("C", "D")
        self.play(Create(p1))
        self.wait(.25)

        self.play(FadeIn(algo[2]))
        self.wait(.25)
        count = Text("1", color=YELLOW)
        count.next_to(graph.points["D"], UP)
        self.play(FadeIn(count))
        self.wait(.25)
        
        self.play(FadeIn(algo[3]))
        self.wait(.25)
        self.play(FadeIn(algo[4]))
        self.wait(.25)
        
        p2 = graph.highlight_path("D", "E")
        self.play(AnimationGroup(
            Create(p2),
            Transform(count, Text("2", color=YELLOW).next_to(graph.points["E"], UP+RIGHT))
            ))
        self.wait(.25)
        
        p3 = graph.highlight_path("E", "F")
        self.play(AnimationGroup(
            Create(p3),
            Transform(count, Text("3", color=YELLOW).next_to(graph.points["F"], RIGHT))
            ))
        self.wait(.25)
        
        self.play(AnimationGroup(
            FadeIn(algo[5]),
            FadeIn(algo[6])
            ))
        self.wait(.25)

        graph.invert_path("C", "D", "E", "F")
        
        self.play(AnimationGroup(
            FadeOut(count),
            graph.points["C"].animate.set_fill(WHITE),
            *graph.update_matching()
            ))
        self.wait(.25)
        
        self.play(AnimationGroup(
            *(FadeOut(p) for p in [p1, p2, p3])
            ))
        self.wait(.25)

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
        self.wait(.25)


        
class AugmentAlgorithmCounterexample(Scene):
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
        self.wait(.25)
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
        self.wait(.25)
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
            self.wait(.25)

        # self.play(AnimationGroup(
        #     *[graph.points[p].animate.set_fill(BLUE_D) for p in p1_points],
        #     *[graph.lines[(p1_points[i], p1_points[i + 1])].animate.set_stroke(BLUE_D) for i in range(5)]
        # ))
        # self.play(AnimationGroup(
        #     *[p.animate.set_stroke(BLUE, opacity=0.7, z_index=-1) for p in p1]
        # ))
        # self.wait(.25)
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
        self.wait(.25)
        p3 = graph.highlight_path("E", "F")
        self.play(Create(p3))
        self.play(Uncreate(p3))
        self.wait(.25)
        
        p3 = graph.highlight_path("E", "D", "C", "B")
        self.play(AnimationGroup(
            Create(p3),
            Transform(count, Text("4", color=YELLOW).next_to(graph.points["B"], DOWN)),
            ))
        self.wait(.25)


class BipartiteAnimation(Scene):
    def construct(self):
        graph = _make_even_cycle_graph()
        graph.draw_edges(self)
        graph.draw_points(self)
        self.wait(.25)
        y = 2
        x = -1
        dx = 1.8
        dy = sqrt(4 - dx ** 2)
        self.play(graph.rearange({
            "A": [x+dx, y-0*dy, 0],
            "B": [x   , y-1*dy, 0],
            "C": [x+dx, y-2*dy, 0],
            "D": [x   , y-2*dy, 0],
            "E": [x+dx, y-3.5*dy, 0],
            "F": [x   , y-3.5*dy, 0],
        }))
        self.wait(.25)


class Blossom(Scene):
    def construct(self):
        graph_points = {
            "A": np.array([-2 * sin(2*pi/5),    2 * cos(2*pi/5), 0]),
            "B": np.array([ 0,                  2,               0]),
            "C": np.array([ 2 * sin(2*pi/5),    2 * cos(2*pi/5), 0]),
            "D": np.array([ 2 * sin(4*pi/5),   -2 * cos(  pi/5), 0]),
            "E": np.array([-2 * sin(4*pi/5),   -2 * cos(  pi/5), 0]),
            "F": np.array([-2 * sin(4*pi/5)-2, -2 * cos(  pi/5), 0]),
        }
        graph = Graph(graph_points)
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
        self.wait(.25)

        self.play(AnimationGroup(
            FadeOut(graph.points["F"]),
            FadeOut(graph.lines[("E","F")])
            ))
        self.wait(.25)
        graph_abcde = graph.get_sub_group(["A", "B", "C", "D", "E"])
        self.play(Indicate(graph_abcde))
        self.wait(.25)
        blossom = Tex(r"Blossom\\", r"$2k+1$").to_edge(UP)
        
        self.play(Write(blossom[0])),
        self.play(Write(blossom[1])),
        
        self.wait(.25)
        l1 = graph.get_sub_group(["B", "C"])
        l2 = graph.get_sub_group(["D", "E"])
        self.play(LaggedStart(
            Indicate(l1),
            Indicate(l2),
            lag_ratio=0.2
        ))
        self.wait(.25)
        k_2 = MathTex("k=2").to_edge(DOWN, buff=1)
        self.play(Write(k_2))
        self.wait(.25)

        aa = graph_points["A"] + np.array([-1, 0, 0])
        cc = graph_points["C"] + np.array([ 1, 0, 0])
        dd = graph_points["D"] + (graph_points["C"] - graph_points["B"]) / 2
        ee = graph_points["E"] + (graph_points["A"] - graph_points["B"]) / 2

        aa_edge = graph.UnconnectedEdge(graph_points["A"], aa)
        cc_edge = graph.UnconnectedEdge(graph_points["C"], cc)
        dd_edge = graph.UnconnectedEdge(graph_points["D"], dd)
        ee_edge = graph.UnconnectedEdge(graph_points["E"], ee)

        self.play(AnimationGroup(
            *[FadeIn(e) for e in [aa_edge, cc_edge, dd_edge, ee_edge]]
        ))
        self.wait(.25)

        aa_solid = graph.ConnectedEdge(graph_points["A"], aa)
        self.play(AnimationGroup(
            Create(aa_solid),
            FadeOut(aa_edge)
            ))
        self.wait(.25)

        origin = [0, 0, 0]
        self.play(AnimationGroup(
            *[graph.points[p].animate.move_to(origin) for p in ["A", "B", "C", "D", "E"]],
            *[graph.lines[e].animate.put_start_and_end_on(origin, origin) for e in [
                ("A", "B"),
                ("B", "C"),
                ("C", "D"),
                ("D", "E"),
                ("A", "E")]],
            ))
        self.wait(.25)
        self.play(AnimationGroup(
            # *[l.animate.put_start_and_end_on(origin, l.get_end()) for l in [aa_solid, cc_edge, dd_edge, ee_edge]]
            Transform(aa_solid, graph.ConnectedEdge(origin, aa_solid.get_end())),
            *[Transform(l, graph.UnconnectedEdge(origin, l.get_end())) for l in [cc_edge, dd_edge, ee_edge]]
            ))
        self.wait(.25)
        aa_edge = graph.UnconnectedEdge(origin, aa_solid.get_end())
        self.play(AnimationGroup(
            ShrinkToCenter(aa_solid),
            FadeIn(aa_edge),
        ))
        self.wait(.25)
