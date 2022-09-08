from io import BytesIO
from networkx import Graph, spring_layout
from PIL import Image, ImageDraw, ImageFont
from database import Person
import copy
import numpy as np
import requests


def count_people(person, people):
    return len([target for target in people if target.id == person.id])

def get_name(i, downward=True):
    if not i:
        return "you"
    else:
        return "grand" * (i-1) + ("child" if downward else "parent") + " or their peer"


def remove_duplicates(people):
    output = copy.copy(people)
    for person in people:
        while count_people(person, output) > 1:
            for i, target in enumerate(output):
                if target.id == person.id:
                    del output[i]
                    break
    return people


def calculate_generations(person, direction_children=True, steps=2):
    generations = [[(True, person)]]  # (isDirect, person)
    partner_map_global = {}
    descendance_map = {}
    people = [person]
    for i in range(steps):
        generations.append([])
        for _, person in generations[-2]:
            if direction_children:
                appended = person.get_children()
            else:
                appended = person.get_parents()
            descendance_map[person.id] = appended
            people += appended
            all_partners = []
            for p in appended:
                partner_map, partners = p.get_partners()
                for partner in partners:
                    all_partners.append(partner)
                for partner, partners in partner_map.items():
                    all_partners += partners
                    partner_map_global[partner] = partners
            all_partners = remove_duplicates(all_partners)
            people += all_partners
            for person in all_partners:
                generations[-1].append((person in appended, person))
    return generations, partner_map_global, descendance_map, remove_duplicates(people)


def calculate_generation_mapping(generations):
    people = {}
    for i, generation in enumerate(generations):
        for isDirect, person in generation:
            people[person.id] = people.get(person.id, []) + [(isDirect, i)]
    return people


def calculate_graph_like_object(partner_map, descendance_map):
    links = []
    for person, descendants in descendance_map.items():
        for descendant in descendants:
            links.append(tuple(sorted([person, descendant.id])))
    for person, descendants in partner_map.items():
        for descendant in descendants:
            links.append(tuple(sorted([person, descendant.id])))
    return list(set(links))


def calculate_nx_graph(graph_like_object, nodes):
    graph = Graph()
    for node in nodes:
        graph.add_node(node.id)
    for link in graph_like_object:
        graph.add_edge(*link)
    return graph


def calculate_people_coordinates(graph, person):
    positions = spring_layout(graph, dim=2, pos={person.id: (0, 0)}, fixed=[person.id])
    return positions


def person_to_generations_and_coordinates(person, direction_children=True, steps=2):
    generations, partner_map, descendance_map, nodes = calculate_generations(
        person, direction_children, steps
    )
    generation_mapping = calculate_generation_mapping(generations)
    graph_like_object = calculate_graph_like_object(partner_map, descendance_map)
    nx_graph = calculate_nx_graph(graph_like_object, nodes)
    positions = calculate_people_coordinates(nx_graph, person)
    return generation_mapping, positions, graph_like_object


def render(positions, links, generation_mapping, profile_picture_map, username_map, downward=True):
    generation_colors = [
        (163, 190, 140),
        (235, 203, 139),
        (208, 135, 112),
        (191, 97, 106),
        (180, 142, 173),
    ]
    scale = 1024

    bounds = [0, 0, 0, 0]  # min x; min y; max x; max y
    bounds[0] = min(position[0] for position in positions.values())
    bounds[1] = min(position[1] for position in positions.values())
    bounds[2] = max(position[0] for position in positions.values())
    bounds[3] = max(position[1] for position in positions.values())

    # Place person in center
    bounds[0], bounds[2] = -max(abs(bounds[0]), abs(bounds[2])), max(
        abs(bounds[0]), abs(bounds[2])
    )
    bounds[1], bounds[3] = -max(abs(bounds[1]), abs(bounds[3])), max(
        abs(bounds[1]), abs(bounds[3])
    )

    size = ((bounds[2] - bounds[0] + 2) * scale, (bounds[3] - bounds[1] + 2) * scale)
    size = [int(x) for x in size]
    offset = [bounds[0], bounds[1]]

    image = Image.new("RGB", size, (46, 52, 64))
    draw = ImageDraw.Draw(image)

    thickness = max(int(0.025 * scale), 1)
    for link in links:
        coords = list(
            np.uint64(
                np.concatenate(
                    [
                        positions[link[0]] - offset + [1, 1],
                        positions[link[1]] - offset + [1, 1],
                    ]
                )
                * scale
            )
        )
        draw.line(coords, (94, 129, 172), thickness)

    pfp_size_in_pixels = [int(0.2 * scale), int(0.2 * scale)]
    mask = Image.new("L", pfp_size_in_pixels)
    ImageDraw.Draw(mask).ellipse([0, 0] + pfp_size_in_pixels, 255)
    font = ImageFont.truetype("impact.ttf", int(0.0625 * scale))
    for user_id, position in positions.items():
        # We have to draw the genreration pie chart first
        slices = len(generation_mapping[user_id])
        for i, slice in enumerate(generation_mapping[user_id]):
            draw.pieslice(
                [
                    int(x)
                    for x in list(
                        np.concatenate(
                            (
                                position
                                - ([0.125, 0.125] if slice[0] else [0.1125, 0.1125])
                                - offset,
                                position
                                + ([0.125, 0.125] if slice[0] else [0.1125, 0.1125])
                                - offset,
                            )
                        )
                        * scale
                        + [scale, scale, scale, scale]
                    )
                ],
                360 / slices * i,
                360 / slices * (i + 1),
                fill=generation_colors[slice[1] % len(generation_colors)],
            )

        url = profile_picture_map[user_id]
        if url:
            pfp = (
                Image.open(BytesIO(requests.get(url).content))
                .convert("RGB")
                .resize(pfp_size_in_pixels)
            )
            image.paste(
                pfp,
                [
                    int(x)
                    for x in list(
                        (position - [0.1, 0.1] - offset) * scale + [scale, scale]
                    )
                ],
                mask,
            )

        padding = int(0.0625 / 2 * scale)
        text = username_map[user_id]
        text_coords = [
            int(x)
            for x in list((position + [0, 0.125] - offset) * scale + [scale, scale])
        ]
        text_size = draw.textsize(text, font=font)
        text_coords[0] -= text_size[0] // 2
        text_coords[1] += padding
        box = [
            text_coords[0] - padding,
            text_coords[1] - padding,
            text_coords[0] + text_size[0] + padding,
            text_coords[1] + text_size[1] + padding,
        ]
        draw.rounded_rectangle(box, padding, (59, 66, 82))
        draw.text(text_coords, text, (236, 239, 244), font=font)

    n_generations = max(max([generation[1] for generation in person]) for person in generation_mapping.values())
    for i in range(n_generations+1):
        draw.ellipse(
            [
                int(scale*0.125),
                int(scale*(i+1)*0.125),
                int(scale*0.1875),
                int(scale*(i+1.5)*0.125),
            ],
            fill=generation_colors[i%len(generation_colors)]
        )
        draw.text(
            [int(scale*0.25), int(scale*(i+1)*0.125)],
            text=get_name(i, downward=downward),
            font=font
        )

    return image
