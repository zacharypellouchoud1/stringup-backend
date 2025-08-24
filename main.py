from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Session, select, create_engine
from pydantic import BaseModel
from sqlmodel import Session
from fastapi import Depends


# ---------- DB Models ----------

class Stringer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    rate_per_racket: float
    availability: str
    capacity_today: int
    rating_quality: float
    rating_punctuality: float
    location: str

class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    stringer_id: int
    player_name: str
    notes: Optional[str] = None

# ---------- DB Setup ----------

engine = create_engine("sqlite:///./stringup.db", echo=False)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
    # seed once if empty
    with Session(engine) as s:
        has_any = s.exec(select(Stringer)).first()   # <-- check if any row exists
        if not has_any:
            s.add_all([
                Stringer(name="Alex Kim", rate_per_racket=22.0, availability="Today 1–5pm",
                        capacity_today=4, rating_quality=4.8, rating_punctuality=4.6, location="La Jolla"),
                Stringer(name="Maria G", rate_per_racket=18.0, availability="Today 3–8pm",
                        capacity_today=6, rating_quality=4.5, rating_puncwwwwwtuality=4.9, location="UTC"),
                Stringer(name="Jay S", rate_per_racket=25.0, availability="Tomorrow 9–2pm",
                        capacity_today=0, rating_quality=4.9, rating_punctuality=4.7, location="PB"),
            ])
            s.commit()

# ---------- API ----------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BookingIn(BaseModel):
    stringer_id: int
    player_name: str
    notes: str | None = None

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/stringers", response_model=List[Stringer])
def list_stringers(session: Session = Depends(get_session)):
    return session.exec(select(Stringer)).all()

@app.get("/stringers/{stringer_id}", response_model=Stringer)
def get_stringer(stringer_id: int, session: Session = Depends(get_session)):
    s = session.get(Stringer, stringer_id)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    return s

@app.post("/bookings")
def create_booking(payload: BookingIn, session: Session = Depends(get_session)):
    s = session.get(Stringer, payload.stringer_id)
    if not s:
        raise HTTPException(status_code=404, detail="Stringer not found")
    # reduce capacity if possible
    if s.capacity_today > 0:
        s.capacity_today -= 1
    session.add(Booking(stringer_id=payload.stringer_id,
                        player_name=payload.player_name,
                        notes=payload.notes))
    session.add(s)
    session.commit()
    return {"ok": True}

class StringerIn(BaseModel):
    name: str
    rate_per_racket: float
    availability: str
    capacity_today: int
    rating_quality: float
    rating_punctuality: float
    location: str

@app.post("/stringers", response_model=Stringer)
def create_stringer(payload: StringerIn, session: Session = Depends(get_session)):
    s = Stringer(**payload.model_dump())
    session.add(s)
    session.commit()
    session.refresh(s)
    return s
