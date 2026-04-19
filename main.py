from fastapi import FastAPI, Response
from starlette.status import HTTP_200_OK,HTTP_201_CREATED,HTTP_204_NO_CONTENT
from model.user_connection import UserConecction
from schema.user_schema import UserSchema

app = FastAPI()
conn = UserConecction()

@app.get("/", status_code=HTTP_200_OK)
async def root():
    item = []
    for data in conn.read_all(): ##dar formato JSON a los datos obtenidos
        dictionary = {}
        dictionary["id"] = data[0]
        dictionary["name"] = data[1]
        dictionary["email"] = data[2]
        dictionary["password"] = data[3]
        dictionary["phone"] = data[4]
        dictionary["location"] = data[5]
        item.append(dictionary)
    return item


@app.get("/api/user/{id}", status_code=HTTP_200_OK)
async def get_one(id: str):
    dictionary = {}
    data = conn.read_one(id)
    dictionary["id"] = data[0]
    dictionary["name"] = data[1]
    dictionary["email"] = data[2]
    dictionary["password"] = data[3]
    dictionary["phone"] = data[4]
    dictionary["location"] = data[5]
    return dictionary


@app.post("/api/insert_user", status_code=HTTP_201_CREATED)
async def insert_user(user_data: UserSchema):
    data = user_data.dict()
    data.pop("id") ##eliminamos el id porque es autoincremental
    conn.write(data)
    return Response(status_code=HTTP_201_CREATED)


@app.put("/api/update_user/{id}", status_code=HTTP_204_NO_CONTENT)
async def update_user(id: str, user_data: UserSchema):
    data = user_data.dict()
    data["id"] = id ##agregamos el id al diccionario para la consulta SQL
    conn.update(data)
    return Response(status_code=HTTP_204_NO_CONTENT)


@app.delete("/api/delete_user/{id}", status_code=HTTP_204_NO_CONTENT)
async def delete_user(id: str):
    conn.delete(id)
    return Response(status_code=HTTP_204_NO_CONTENT)
