import math
from datetime import datetime
import sqlite3
import numpy as np
import pyvista as pv
from pyvista import examples
import satkit as sk

import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QDateTimeEdit,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QCheckBox
)
from PySide6.QtCore import QDateTime
from PySide6.QtCore import QTimer

from vtk import vtkTexturedSphereSource

RAGGIO_TERRA = 6371000

nazione = None
categoria_sat= None
categoria_org = None
inizio = None
durata = None
calcolo_visibilita = False
latitudine = None
longitudine = None
vis_inizio = None
vis_durata = None

def query_epoca_max(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(datetime(epoca))
            FROM satellite 
        """)
    row = cursor.fetchone()
    return row[0]

def query_nazione(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT o.nazione
        FROM satellite s
        INNER JOIN organizzazione o ON s.org_gestione=o.nome
        WHERE o.nazione IS NOT NULL
        ORDER BY o.nazione
    """)
    return [row[0] for row in cursor.fetchall()]

def query_cat_sat(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT categoria
        FROM satellite
        WHERE categoria IS NOT NULL
        ORDER BY categoria
    """)
    return [row[0] for row in cursor.fetchall()]

def query_cat_org(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT categoria
        FROM organizzazione
        WHERE categoria IS NOT NULL
        ORDER BY categoria
    """)

    return [row[0] for row in cursor.fetchall()]



def query_satelliti(conn, nazione, categoria_sat, categoria_org):
    query = """
        SELECT s.codice_SCN,s.nome, s.x, s.y, s.z, s.v_x, s.v_y, s.v_z, datetime(s.epoca), s.categoria, o.nome, o.nazione, o.categoria
        FROM satellite s
        INNER JOIN organizzazione o ON s.org_gestione=o.nome
        WHERE 1=1
    """
    parametri = []

    if nazione != "qualsiasi":
        query += " AND o.nazione = ?"
        parametri.append(nazione)
    if categoria_sat != "qualsiasi":
        query += " AND s.categoria = ?"
        parametri.append(categoria_sat)
    if categoria_org != "qualsiasi":
        query += " AND o.categoria = ?"
        parametri.append(categoria_org)

    cursor = conn.cursor()
    cursor.execute(query, parametri)
    righe = cursor.fetchall()

    codici_sat = [r[0] for r in righe]
    nomi  = [r[1] for r in righe]
    stati = np.array([r[2:8] for r in righe], dtype=np.float64)
    epoche = [datetime.fromisoformat(r[8]) for r in righe]
    categorie_sat = [r[9] for r in righe]
    nomi_org = [r[10] for r in righe]
    nazioni = [r[11] for r in righe]
    categorie_org = [r[12] for r in righe]

    return codici_sat,nomi, stati, epoche, categorie_sat, nomi_org, nazioni, categorie_org


def salva(window):
    global nazione, categoria_sat, categoria_org, inizio, durata
    global latitudine, longitudine, vis_inizio, vis_durata, calcolo_visibilita

    nazione = window.nazione_sel.currentText()
    categoria_sat = window.categoria_sat_sel.currentText()
    categoria_org = window.categoria_org_sel.currentText()
    inizio = window.inizio_sel.dateTime().toPython()
    durata = window.durata_sel.value()
    latitudine = window.lat_sel.value()
    longitudine = window.lon_sel.value()
    vis_inizio = window.vis_inizio_sel.dateTime().toPython()
    vis_durata = window.vis_durata_sel.value()
    calcolo_visibilita = window.gruppo_vis.isChecked()

    window.close()


def crea_finestra():
    window = QWidget()
    window.setWindowTitle("Satelliti")
    window.resize(400, 300)
    form = QFormLayout()

    conn = sqlite3.connect("satelliti.db")
    data_min_str=query_epoca_max(conn)
    dt = datetime.strptime(data_min_str, "%Y-%m-%d %H:%M:%S")
    data_min = QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


    nazione_sel = QComboBox()
    nazione_sel.addItem("qualsiasi")
    for k in query_nazione(conn):
        nazione_sel.addItem(k)
    form.addRow("Nazione:", nazione_sel)
       
    categoria_sat_sel = QComboBox()
    categoria_sat_sel.addItem("qualsiasi")
    for k in query_cat_sat(conn):
        categoria_sat_sel.addItem(k)
    form.addRow("categoria satellite:", categoria_sat_sel)
    
    categoria_org_sel = QComboBox()
    categoria_org_sel.addItem("qualsiasi")
    for k in query_cat_org(conn):
        categoria_org_sel.addItem(k)
    form.addRow("categoria organizzazione:", categoria_org_sel)

    inizio_sel = QDateTimeEdit()
    inizio_sel.setDisplayFormat("dd-MM-yyyy HH:mm")
    inizio_sel.setMinimumDateTime(data_min)
    inizio_sel.setDateTime(data_min)
    form.addRow("Data inizio visualizzazione:", inizio_sel)

    durata_sel = QSpinBox()
    durata_sel.setRange(1, 7)
    durata_sel.setValue(1)
    durata_sel.setSuffix(" giorni")
    form.addRow("Durata della visualizzazione:", durata_sel)

    gruppo_vis = QGroupBox("Coordinate punto")
    layout_vis = QFormLayout()
    gruppo_vis.setLayout(layout_vis)
    gruppo_vis.setCheckable(True)
    gruppo_vis.setChecked(False)

    lat_sel = QDoubleSpinBox()
    lat_sel.setRange(-90.0, 90.0)
    lat_sel.setDecimals(6)
    lat_sel.setValue(0)
    lat_sel.setSuffix(" °")
    layout_vis.addRow("Latitudine:", lat_sel)

    lon_sel = QDoubleSpinBox()
    lon_sel.setRange(-180.0, 180.0)
    lon_sel.setDecimals(6)
    lon_sel.setValue(0)
    lon_sel.setSuffix(" °")
    layout_vis.addRow("Longitudine:", lon_sel)

    vis_inizio_sel = QDateTimeEdit()
    vis_inizio_sel.setDisplayFormat("dd-MM-yyyy HH:mm")
    vis_inizio_sel.setMinimumDateTime(data_min)
    vis_inizio_sel.setDateTime(data_min)
    layout_vis.addRow("Inizio intervallo:", vis_inizio_sel)

    vis_durata_sel = QSpinBox()
    vis_durata_sel.setRange(1, 1440)
    vis_durata_sel.setValue(60)
    vis_durata_sel.setSuffix(" minuti")
    layout_vis.addRow("Durata intervallo:", vis_durata_sel)

    run_button = QPushButton("Simulazione")
    run_button.clicked.connect(lambda: salva(window))

    window.nazione_sel = nazione_sel
    window.categoria_sat_sel = categoria_sat_sel
    window.categoria_org_sel = categoria_org_sel
    window.inizio_sel = inizio_sel
    window.durata_sel = durata_sel
    window.lat_sel = lat_sel
    window.lon_sel = lon_sel
    window.vis_inizio_sel = vis_inizio_sel
    window.vis_durata_sel = vis_durata_sel
    window.gruppo_vis = gruppo_vis

    layout = QVBoxLayout()
    layout.addLayout(form)
    layout.addWidget(gruppo_vis)
    layout.addWidget(run_button)
    window.setLayout(layout)

    conn.close() 

    window.show()
    return window


def simulazione(t0,orbite,codici_sat, nomi, categorie_sat, nazioni, nomi_org, categorie_org,latitudine,longitudine):  
    N = len(orbite)
    if N == 0:
        frames = 0
    else:
        frames = len(orbite[0])-1
    frame = 0
    satellite_selezionato = 0
    playing = True

    def matrice_rotazione(time):
        q = sk.frametransform.rotation(
            from_frame=sk.frame.ITRF,
            to_frame=sk.frame.GCRF,
            tm=time,
        )

        return q.as_rotation_matrix()

    def punti_cerchio(sat_pos, angolo):

        Re = RAGGIO_TERRA*1.0001
        rs = np.linalg.norm(sat_pos)

        e = np.radians(angolo)

        psi = np.arccos(
            (Re / rs) * np.cos(e)
        ) - e

        u = sat_pos / rs

        ref = np.array([0.0, 0.0, 1.0])

        if abs(np.dot(u, ref)) > 0.9:
            ref = np.array([1.0, 0.0, 0.0])

        e1 = np.cross(u, ref)
        e1 /= np.linalg.norm(e1)

        e2 = np.cross(u, e1)
        e2 /= np.linalg.norm(e2)

        theta = np.linspace(0, 2*np.pi, 100)

        points = Re * (
            np.cos(psi) * u
            + np.sin(psi) *
            (
                np.cos(theta)[:, None] * e1
                + np.sin(theta)[:, None] * e2
            )
        )
        return points

    plotter = pv.Plotter(window_size=(1200, 800))
    terra = examples.planets.load_earth(radius=RAGGIO_TERRA,lat_resolution=360,lon_resolution=180)
    terra.rotate_z(180, inplace=True) 
    texture = examples.load_globe_texture()

    terra_attore = plotter.add_mesh(
        terra,
        texture=texture, 
        smooth_shading=True,
        pickable=False
    )
    terra_attore.rotation_from(matrice_rotazione(t0))
    

    if calcolo_visibilita==True:
        v_itrf=sk.itrfcoord(latitude_deg=latitudine, longitude_deg=longitudine, altitude=0).vector
        point_polydata = pv.PolyData(matrice_rotazione(t0) @ v_itrf)  
        punto_attore = plotter.add_mesh(
            point_polydata,
            color="red",
            point_size=15,
            render_points_as_spheres=True,
            pickable=False
        )

    for i in range(N):
        orbit = pv.lines_from_points(orbite[i], close=False,)
        plotter.add_mesh(orbit, color="royalblue",line_width=2,pickable=False)

    sat_punti = pv.PolyData(orbite[:, 0])

    plotter.add_mesh(
        sat_punti, 
        color="red", 
        point_size=8, 
        render_points_as_spheres=True, 
        pickable=True)


    evidenziatore = pv.PolyData(orbite[satellite_selezionato, frame])

    plotter.add_mesh( 
        evidenziatore, 
        color="yellow", 
        point_size=15, 
        render_points_as_spheres=True, 
        pickable=False
    )

    cerchio = pv.lines_from_points(punti_cerchio(orbite[satellite_selezionato, frame],angolo=10))

    plotter.add_mesh(cerchio, color="yellow",line_width=2,pickable=False)

    info_sat = plotter.add_text(
        "",
        position="lower_left",
        font_size=12
    )  

    plotter.add_text(
        "Selezionare satelliti con il tasto sinistro del mouse \n" 
        "Fermare la visualizzazione con la barra spaziatrice",
        position="upper_left",
        font_size=12
    )  

    def pick_callback(input):
            nonlocal satellite_selezionato
            for n in range (N):
                if(abs(orbite[n, frame][0]-input[0])+abs(orbite[n, frame][1]-input[1])<100): 
                    satellite_selezionato=n
                    break
            refresh_grafica(frame)   
    
    def refresh_grafica(frame):
        tm = t0 + sk.duration(minutes=frame)
        rotazione=matrice_rotazione(tm)
        terra_attore.rotation_from(rotazione)
        if calcolo_visibilita:
            point_polydata.points = matrice_rotazione(tm) @ v_itrf
        sat_punti.points = orbite[:,frame]
        posizione = orbite[satellite_selezionato,frame]
        evidenziatore.points = posizione
        cerchio.points=punti_cerchio(orbite[satellite_selezionato, frame],angolo=10)
        altitude=np.linalg.norm(posizione)-RAGGIO_TERRA
        info_sat.set_text("lower_left",
            f"Codice SCN: {codici_sat[satellite_selezionato]}\n"
            f"Nome: {nomi[satellite_selezionato]}\n"
            f"Categoria: {categorie_sat[satellite_selezionato]}\n"
            f"Nazione organizzazione: {nazioni[satellite_selezionato]}\n"
            f"Nome organizzazione: {nomi_org[satellite_selezionato]}\n"
            f"Categoria organizzazione: {categorie_org[satellite_selezionato]}\n"
            f"Data e ora: {tm.strftime('%d-%m-%Y %H:%M:%S')}\n"
            f"Altitudine: {altitude/1000:.1f} km\n"
        )
        tm = t0 + sk.duration(minutes=frame)

        plotter.render()

    def frame_successiva():
        nonlocal frame
        frame += 1
        if frame>=frames:frame=0
        refresh_grafica(frame)

    def frame_precedente():
        nonlocal frame
        frame -= 1
        refresh_grafica(frame)

    def timer():
        if playing:
            frame_successiva()

    def play():
        nonlocal playing
        playing = not playing

    qt_timer = QTimer()
    qt_timer.timeout.connect(timer)
    qt_timer.start(50)

    plotter.add_key_event("space", play)
    plotter.add_key_event("Right", frame_successiva)
    plotter.add_key_event("Left", frame_precedente)

    plotter.camera_position = [
        (2e7, 2e7, 1.5e7),
        (0, 0, 0),
        (0, 0, 1),
    ]
    plotter.enable_point_picking(
        callback=pick_callback,
        tolerance=0.01,
        left_clicking=True,
        picker='point',
        show_message=False,
        font_size=18,
        show_point=False,
        use_picker=False,
        pickable_window=False,
        clear_on_no_selection=True,
    )   

    plotter.enable_trackball_style()

    plotter.show()
    plotter.close()


app = QApplication(sys.argv)
finestra = crea_finestra()
app.exec()

conn = sqlite3.connect("satelliti.db")

codici_sat, nomi, stati, epoche, categorie_sat, nomi_org, nazioni, categorie_org = query_satelliti(conn, nazione, categoria_sat, categoria_org)

epoca_min = min(epoche)
delta = inizio - epoca_min
delta_vis = vis_inizio - epoca_min
giorni_min = math.ceil(delta.total_seconds() / (24 * 3600))
giorni_min_vis = math.ceil(delta.total_seconds() / (24 * 3600))

N_satelliti=len(stati)
N_punti=durata*24*60

t_inizio=sk.time.from_datetime(inizio)
epoche_sk = np.array([sk.time.from_datetime(dt) for dt in epoche], dtype=object)

orbite = []

if calcolo_visibilita:
    codici_sat_out = []
    nomi_out = []
    categorie_sat_out = []
    nazioni_out = []
    nomi_org_out = []
    categorie_org_out = []
    t_inizio_vis=sk.time.from_datetime(vis_inizio)
    punto_itrf_coordinate=sk.itrfcoord(latitude_deg=latitudine, longitude_deg=longitudine, altitude=0)
    punto_posizioni = np.empty((vis_durata,3))
    punto_vettore = np.empty((vis_durata,3))

    for k in range(vis_durata):
        t = t_inizio_vis + sk.duration(minutes=k)
        rotation = sk.frametransform.rotation(from_frame=sk.frame.ITRF, to_frame=sk.frame.GCRF, tm=t)
        punto_posizioni[k] = rotation * punto_itrf_coordinate.vector
        punto_vettore[k]=punto_posizioni[k]/np.linalg.norm(punto_posizioni[k])

    for i in range(N_satelliti):
        visibile = False
        coseno_minimo=np.cos(np.radians(80))
        result=sk.propagate(stati[i], epoche_sk[i], duration_days=(giorni_min_vis+1))
        for k in range(vis_durata):
            t = t_inizio_vis + sk.duration(minutes=k)
            position = result.interp(t)[:3]-punto_posizioni[k]
            coseno_angolo=np.dot(punto_vettore[k],position/np.linalg.norm(position))
            if(coseno_angolo>coseno_minimo):
                visibile=True
                break
        if(visibile==True):
            output=np.empty((N_punti, 3), dtype=np.float32)
            result = sk.propagate(stati[i], epoche_sk[i], duration_days=(durata+giorni_min))
            for k in range(N_punti):
                t = t_inizio + sk.duration(minutes=k)
                output[k] = result.interp(t)[:3]
            orbite.append(output)
            codici_sat_out.append(codici_sat[i])
            nomi_out.append(nomi[i])
            categorie_sat_out.append(categorie_sat[i])
            nazioni_out.append(nazioni[i])
            nomi_org_out.append(nomi_org[i])
            categorie_org_out.append(categorie_org[i])
    if not orbite:
        print("Nessun satellite soddisfa le condizioni")
        sys.exit(0)
    orbite=np.array(orbite)
    simulazione(t_inizio, orbite, codici_sat_out, nomi_out, categorie_sat_out, nazioni_out, nomi_org_out, categorie_org_out, latitudine, longitudine)
else:
    for i in range(N_satelliti):
        output = np.empty((N_punti, 3), dtype=np.float32)
        result = sk.propagate(stati[i], epoche_sk[i], duration_days=(durata+giorni_min))
        for k in range(N_punti):
            t = t_inizio + sk.duration(minutes=k)
            output[k] = result.interp(t)[:3]
        orbite.append(output)
    if not orbite:
        print("Nessun satellite soddisfa le condizioni")
        sys.exit(0)
    orbite=np.array(orbite)
    simulazione(t_inizio, orbite, codici_sat, nomi, categorie_sat, nazioni, nomi_org, categorie_org, latitudine, longitudine)