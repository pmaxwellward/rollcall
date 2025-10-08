from google.genai import types

PAIR_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "entries": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "key":    types.Schema(type=types.Type.STRING),
                    "values": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                },
                required=["key", "values"],
            ),
        )
    },
    required=["entries"],
)

REFINE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={"title": types.Schema(type=types.Type.STRING)},
    required=["title"],
)