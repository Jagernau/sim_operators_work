
from database import crud
from datetime import datetime

start = datetime.now()
crud.dubles_sim_clear()
end = datetime.now()

print(f"Успешно {end - start}")
