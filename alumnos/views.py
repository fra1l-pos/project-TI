import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

from usuarios.models import Usuario
from pagos.models import AnioAcademico, PensionMensual
from .models import Alumno
from .forms import AlumnoForm, AlumnoEditForm, GRADOS_CHOICES, SECCIONES_CHOICES, MESES_CHOICES

def is_admin(user):
    return user.is_authenticated and not user.es_padre

@login_required
@user_passes_test(is_admin)
def lista_alumnos(request):
    anio_reciente = AnioAcademico.objects.order_by('-anio').first()
    alumnos = Alumno.objects.all().select_related('padre').order_by('grado', 'apellidos')
    context = {
        'alumnos': alumnos,
        'anio_reciente': anio_reciente,
    }
    return render(request, 'alumnos/lista.html', context)

@login_required
@user_passes_test(is_admin)
def crear_alumno(request):
    """
    Registra un alumno nuevo.
    El apoderado se busca primero por DNI (via AJAX). Si no existe, se crea en el mismo POST.
    """
    errores = {}

    if request.method == 'POST':
        # ── 1. Resolver apoderado ──────────────────────────────────────────
        padre_id    = request.POST.get('padre_id', '').strip()
        dni_nuevo   = request.POST.get('dni_nuevo', '').strip()
        nom_nuevo   = request.POST.get('nuevo_nombres', '').strip()
        ape_nuevo   = request.POST.get('nuevo_apellidos', '').strip()
        cel_nuevo   = request.POST.get('nuevo_celular', '').strip()
        email_nuevo = request.POST.get('nuevo_email', '').strip()

        padre = None
        if padre_id:
            # Apoderado ya encontrado por búsqueda AJAX
            try:
                padre = Usuario.objects.get(pk=int(padre_id), es_padre=True)
            except (Usuario.DoesNotExist, ValueError):
                errores['apoderado'] = 'El apoderado seleccionado no existe. Busca nuevamente.'
        elif dni_nuevo:
            # Crear apoderado nuevo
            if not nom_nuevo:
                errores['nuevo_nombres'] = 'Ingresa el nombre del apoderado.'
            if not ape_nuevo:
                errores['nuevo_apellidos'] = 'Ingresa los apellidos del apoderado.'
            if not errores:
                if Usuario.objects.filter(username=dni_nuevo).exists():
                    # Ya existe pero quizás no como padre: reutilizar
                    padre = Usuario.objects.get(username=dni_nuevo)
                    if not padre.es_padre:
                        padre.es_padre = True
                        padre.save()
                else:
                    padre = Usuario.objects.create_user(
                        username=dni_nuevo,
                        password=dni_nuevo,
                        first_name=nom_nuevo,
                        last_name=ape_nuevo,
                        telefono=cel_nuevo or None,
                        email=email_nuevo or '',
                        es_padre=True,
                    )
        else:
            errores['apoderado'] = 'Busca un apoderado por DNI o regístralo como nuevo.'

        # ── 2. Validar datos del alumno ────────────────────────────────────
        nombres    = request.POST.get('nombres', '').strip()
        apellidos  = request.POST.get('apellidos', '').strip()
        grado_niv  = request.POST.get('grado_nivel', '').strip()
        seccion    = request.POST.get('seccion', '').strip()
        mes_raw    = request.POST.get('mes_ingreso', '3').strip()
        activo     = request.POST.get('activo') == 'on'

        if not nombres:
            errores['nombres'] = 'Ingresa el nombre del alumno.'
        if not apellidos:
            errores['apellidos'] = 'Ingresa los apellidos del alumno.'
        if not grado_niv:
            errores['grado_nivel'] = 'Selecciona el grado.'
        if not seccion:
            errores['seccion'] = 'Selecciona la sección.'

        try:
            mes_ingreso = int(mes_raw)
        except ValueError:
            mes_ingreso = 3

        # ── 3. Guardar si no hay errores ───────────────────────────────────
        if not errores and padre:
            grado_completo = f"{grado_niv} {seccion}".strip()
            alumno = Alumno.objects.create(
                padre=padre,
                nombres=nombres,
                apellidos=apellidos,
                grado=grado_completo,
                mes_ingreso=mes_ingreso,
                activo=activo,
            )
            # Auto-generar pensiones del año en curso
            anio_reciente = AnioAcademico.objects.order_by('-anio').first()
            pensiones_creadas = 0
            if anio_reciente:
                for mes in range(max(3, alumno.mes_ingreso), 13):
                    fecha_venc = datetime.date(anio_reciente.anio, mes, 28)
                    _, created = PensionMensual.objects.get_or_create(
                        alumno=alumno, anio_academico=anio_reciente, mes=mes,
                        defaults={'monto_deuda': anio_reciente.pension_base,
                                  'fecha_vencimiento': fecha_venc, 'pagado': False}
                    )
                    if created:
                        pensiones_creadas += 1
                messages.success(request, f'Alumno {alumno} registrado. Se generaron {pensiones_creadas} mensualidades para el año {anio_reciente.anio}.')
            else:
                messages.success(request, f'Alumno {alumno} registrado correctamente.')
            return redirect('lista_alumnos')

        # Hay errores: re-renderizar con datos previos y errores
        post_data = request.POST
        return render(request, 'alumnos/crear_alumno.html', {
            'errores': errores,
            'post_data': post_data,
            'padre_encontrado': padre,
            'grados': GRADOS_CHOICES[1:],
            'secciones': SECCIONES_CHOICES[1:],
            'meses': MESES_CHOICES,
        })

    # GET
    return render(request, 'alumnos/crear_alumno.html', {
        'grados': GRADOS_CHOICES[1:],
        'secciones': SECCIONES_CHOICES[1:],
        'meses': MESES_CHOICES,
        'errores': {},
    })

@login_required
@user_passes_test(is_admin)
def editar_alumno(request, id):
    alumno = get_object_or_404(Alumno, id=id)
    
    # Separar grado y sección del campo combinado almacenado
    partes_grado = alumno.grado.rsplit(' ', 1)
    grado_actual  = partes_grado[0] if len(partes_grado) > 1 else alumno.grado
    seccion_actual = partes_grado[1] if len(partes_grado) > 1 and len(partes_grado[1]) == 1 else ''

    errores = {}
    if request.method == 'POST':
        nombres   = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        grado_niv = request.POST.get('grado_nivel', '').strip()
        seccion   = request.POST.get('seccion', '').strip()
        mes_raw   = request.POST.get('mes_ingreso', '3').strip()
        activo    = request.POST.get('activo') == 'on'

        if not nombres:   errores['nombres']   = 'Campo requerido.'
        if not apellidos: errores['apellidos'] = 'Campo requerido.'
        if not grado_niv: errores['grado_nivel'] = 'Selecciona el grado.'
        if not seccion:   errores['seccion']   = 'Selecciona la sección.'

        if not errores:
            alumno.nombres    = nombres
            alumno.apellidos  = apellidos
            alumno.grado      = f"{grado_niv} {seccion}".strip()
            alumno.mes_ingreso = int(mes_raw) if mes_raw.isdigit() else 3
            alumno.activo     = activo
            alumno.save()
            messages.success(request, f'Datos de {alumno} actualizados correctamente.')
            return redirect('lista_alumnos')

        grado_actual   = grado_niv
        seccion_actual = seccion

    return render(request, 'alumnos/editar_alumno.html', {
        'alumno': alumno,
        'grado_actual': grado_actual,
        'seccion_actual': seccion_actual,
        'grados': GRADOS_CHOICES[1:],
        'secciones': SECCIONES_CHOICES[1:],
        'meses': MESES_CHOICES,
        'errores': errores,
    })

@login_required
@user_passes_test(is_admin)
def buscar_apoderado_por_dni(request):
    """Endpoint AJAX: busca un apoderado por DNI y retorna JSON."""
    dni = request.GET.get('dni', '').strip()
    if not dni:
        return JsonResponse({'encontrado': False, 'error': 'DNI vacío.'})
    try:
        padre = Usuario.objects.get(username=dni)
        return JsonResponse({
            'encontrado': True,
            'id': padre.id,
            'nombre_completo': f"{padre.first_name} {padre.last_name}".strip() or padre.username,
            'celular': padre.telefono or '',
            'email': padre.email or '',
            'es_padre': padre.es_padre,
        })
    except Usuario.DoesNotExist:
        return JsonResponse({'encontrado': False})

@login_required
@user_passes_test(is_admin)
def descargar_plantilla_excel(request):
    """Genera y descarga un archivo Excel (.xlsx) con columnas GRADO y SECCION estandarizadas."""
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Border, Side

    # ── Valores estandarizados ──────────────────────────────────────────────
    GRADOS = [
        # Inicial
        "3 años Inicial",
        "4 años Inicial",
        "5 años Inicial",
        # Primaria
        "1ro Primaria",
        "2do Primaria",
        "3ro Primaria",
        "4to Primaria",
        "5to Primaria",
        "6to Primaria",
        # Secundaria
        "1ro Secundaria",
        "2do Secundaria",
        "3ro Secundaria",
        "4to Secundaria",
        "5to Secundaria",
    ]
    SECCIONES = ["A", "B", "C", "D", "E"]
    MESES = [
        "1 - Enero", "2 - Febrero", "3 - Marzo", "4 - Abril",
        "5 - Mayo", "6 - Junio", "7 - Julio", "8 - Agosto",
        "9 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre",
    ]

    wb = openpyxl.Workbook()

    # ── Hoja de Referencia (oculta) con las listas de validación ───────────
    ws_ref = wb.create_sheet("_Listas")
    ws_ref.sheet_state = 'hidden'
    ws_ref['A1'] = 'GRADOS'
    ws_ref['B1'] = 'SECCIONES'
    ws_ref['C1'] = 'MESES'
    for i, g in enumerate(GRADOS, start=2):
        ws_ref.cell(row=i, column=1, value=g)
    for i, s in enumerate(SECCIONES, start=2):
        ws_ref.cell(row=i, column=2, value=s)
    for i, m in enumerate(MESES, start=2):
        ws_ref.cell(row=i, column=3, value=m)

    # ── Hoja de Referencia VISIBLE para el administrador ───────────────────
    ws_guia = wb.create_sheet("📋 Guía de Valores")
    title_font = Font(name="Calibri", size=13, bold=True, color="14532D")
    subtitle_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    normal_font = Font(name="Calibri", size=10)

    ws_guia['A1'] = "Guía de valores estandarizados para la plantilla"
    ws_guia['A1'].font = title_font
    ws_guia.merge_cells('A1:D1')

    grn = PatternFill(start_color="15803D", end_color="15803D", fill_type="solid")
    gry = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")

    headers_guia = ["GRADO (columna H)", "SECCION (columna I)", "MES_INGRESO (columna J)", "Nota"]
    for c, h in enumerate(headers_guia, start=1):
        cell = ws_guia.cell(row=3, column=c, value=h)
        cell.fill = grn
        cell.font = subtitle_font
        cell.alignment = Alignment(horizontal="center")

    notas = [
        "Selecciona el grado del alumno",
        "Letra de sección (A-E)",
        "Número de mes 1 al 12 (ej. 3 = Marzo)",
        "⚠ El sistema combinará GRADO + SECCION automáticamente",
    ]
    max_rows = max(len(GRADOS), len(SECCIONES), len(MESES), len(notas))
    for row in range(max_rows):
        g_val = GRADOS[row] if row < len(GRADOS) else ""
        s_val = SECCIONES[row] if row < len(SECCIONES) else ""
        m_val = MESES[row] if row < len(MESES) else ""
        n_val = notas[row] if row < len(notas) else ""
        r = row + 4
        for c, v in enumerate([g_val, s_val, m_val, n_val], start=1):
            cell = ws_guia.cell(row=r, column=c, value=v)
            cell.font = normal_font
            if row % 2 == 0:
                cell.fill = gry

    for col_idx in range(1, 5):
        ws_guia.column_dimensions[get_column_letter(col_idx)].width = 30

    # ── Hoja Principal de Datos ────────────────────────────────────────────
    ws = wb.worksheets[0]
    ws.title = "Registro_Alumnos"

    headers = [
        "DNI_APODERADO",      # A - 1
        "NOMBRES_APODERADO",  # B - 2
        "APELLIDOS_APODERADO",# C - 3
        "CELULAR_APODERADO",  # D - 4
        "EMAIL_APODERADO",    # E - 5
        "NOMBRES_ALUMNO",     # F - 6
        "APELLIDOS_ALUMNO",   # G - 7
        "GRADO",              # H - 8  ← separado
        "SECCION",            # I - 9  ← separado
        "MES_INGRESO",        # J - 10
    ]

    # ── Estilos cabecera ───────────────────────────────────────────────────
    header_fill = PatternFill(start_color="14532D", end_color="14532D", fill_type="solid")
    header_fill_data = PatternFill(start_color="166534", end_color="166534", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Fila 1: categorías de grupo
    ws['A1'] = "DATOS DEL APODERADO"
    ws.merge_cells('A1:E1')
    ws['A1'].fill = header_fill
    ws['A1'].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws['A1'].alignment = header_align

    ws['F1'] = "DATOS DEL ALUMNO"
    ws.merge_cells('F1:G1')
    ws['F1'].fill = header_fill_data
    ws['F1'].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws['F1'].alignment = header_align

    ws['H1'] = "GRADO Y SECCIÓN"
    ws.merge_cells('H1:I1')
    ws['H1'].fill = PatternFill(start_color="15803D", end_color="15803D", fill_type="solid")
    ws['H1'].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws['H1'].alignment = header_align

    ws['J1'] = "INGRESO"
    ws['J1'].fill = PatternFill(start_color="166534", end_color="166534", fill_type="solid")
    ws['J1'].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws['J1'].alignment = header_align

    # Fila 2: nombres de columnas
    header_fill2 = PatternFill(start_color="22C55E", end_color="22C55E", fill_type="solid")
    header_font2 = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.row_dimensions[2].height = 30
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=col_idx, value=h)
        cell.fill = header_fill2
        cell.font = header_font2
        cell.alignment = header_align

    ws.row_dimensions[1].height = 22

    # ── Filas de ejemplo ──────────────────────────────────────────────────
    filas_ejemplo = [
        ["45892134", "Juan Carlos",   "Mendoza Flores",  "987654321", "juan.mendoza@email.com",  "Lucas",   "Mendoza Quispe", "3ro Primaria",   "A", 3],
        ["45892134", "Juan Carlos",   "Mendoza Flores",  "987654321", "juan.mendoza@email.com",  "Sofia",   "Mendoza Quispe", "5to Primaria",   "B", 3],
        ["71234567", "Maria Elena",   "Castro Lopez",    "912345678", "maria.castro@email.com",  "Mateo",   "Ramos Castro",   "1ro Secundaria", "B", 3],
        ["40987654", "Pedro Antonio", "Salas Gutierrez", "945612378", "pedro.salas@email.com",   "Valeria", "Salas Vega",     "2do Primaria",   "A", 3],
        ["40987654", "Pedro Antonio", "Salas Gutierrez", "945612378", "pedro.salas@email.com",   "Joaquin", "Salas Vega",     "6to Primaria",   "A", 3],
    ]
    row_fill_alt = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
    data_font = Font(name="Calibri", size=10)
    for i, fila in enumerate(filas_ejemplo):
        r = i + 3
        for col_idx, val in enumerate(fila, start=1):
            cell = ws.cell(row=r, column=col_idx, value=val)
            cell.font = data_font
            if i % 2 == 0:
                cell.fill = row_fill_alt

    # ── Validaciones desplegables (filas 3-200) ────────────────────────────
    n_grados = len(GRADOS) + 1  # +1 por encabezado en _Listas
    n_sec = len(SECCIONES) + 1
    n_meses = len(MESES) + 1

    dv_grado = DataValidation(
        type="list",
        formula1=f"'_Listas'!$A$2:$A${n_grados}",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Grado inválido",
        error="Selecciona un grado de la lista desplegable.",
    )
    dv_grado.sqref = "H3:H200"
    ws.add_data_validation(dv_grado)

    dv_sec = DataValidation(
        type="list",
        formula1=f"'_Listas'!$B$2:$B${n_sec}",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Sección inválida",
        error="Selecciona una sección de la lista (A-E).",
    )
    dv_sec.sqref = "I3:I200"
    ws.add_data_validation(dv_sec)

    dv_mes = DataValidation(
        type="list",
        formula1=f"'_Listas'!$C$2:$C${n_meses}",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Mes inválido",
        error="Selecciona el mes de ingreso de la lista.",
    )
    dv_mes.sqref = "J3:J200"
    ws.add_data_validation(dv_mes)

    # ── Ancho de columnas ──────────────────────────────────────────────────
    anchos = [16, 20, 22, 16, 28, 18, 22, 20, 10, 20]
    for idx, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ancho

    # Congelar fila de encabezados
    ws.freeze_panes = 'A3'

    # Ordenar hojas: Registro primero, Guía segundo, _Listas al final
    wb.move_sheet("Registro_Alumnos", offset=-(len(wb.sheetnames)-1))

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_registro_alumnos.xlsx'
    wb.save(response)
    return response

@login_required
@user_passes_test(is_admin)
def carga_masiva_alumnos(request):
    """Procesa la carga masiva desde un archivo Excel o CSV vinculando alumnos y apoderados."""
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, 'Por favor, selecciona un archivo Excel (.xlsx) o CSV.')
            return redirect('carga_masiva_alumnos')

        nombre = archivo.name.lower()
        if not (nombre.endswith('.xlsx') or nombre.endswith('.xls') or nombre.endswith('.csv')):
            messages.error(request, 'Formato no soportado. Debe ser un archivo .xlsx, .xls o .csv.')
            return redirect('carga_masiva_alumnos')

        try:
            filas_datos = []
            if nombre.endswith('.xlsx') or nombre.endswith('.xls'):
                wb = openpyxl.load_workbook(archivo, data_only=True)
                ws = wb.active
                raw_rows = list(ws.iter_rows(values_only=True))
                if not raw_rows or len(raw_rows) < 2:
                    messages.error(request, 'El archivo no contiene filas de datos.')
                    return redirect('carga_masiva_alumnos')

                headers = [str(h).strip().lower() if h is not None else '' for h in raw_rows[0]]
                for r in raw_rows[1:]:
                    if any(c is not None and str(c).strip() != '' for c in r):
                        filas_datos.append(dict(zip(headers, r)))
            else:
                import csv
                decoded_file = archivo.read().decode('utf-8-sig').splitlines()
                reader = csv.DictReader(decoded_file)
                for row in reader:
                    filas_datos.append({k.strip().lower(): v for k, v in row.items() if k})

            def obtener_campo(fila_dict, *claves_posibles, default=''):
                for clave in claves_posibles:
                    for k, v in fila_dict.items():
                        if clave in k.lower():
                            if v is not None:
                                return str(v).strip()
                return default

            anio_reciente = AnioAcademico.objects.order_by('-anio').first()
            padres_creados = 0
            padres_existentes = 0
            alumnos_creados = 0
            alumnos_existentes = 0
            pensiones_creadas_total = 0
            errores = []

            for num_fila, fila in enumerate(filas_datos, start=2):
                dni_padre = obtener_campo(fila, 'dni_apoderado', 'dni_padre', 'doc', 'dni', 'apoderado')
                nombres_padre = obtener_campo(fila, 'nombres_apoderado', 'nombres_padre', 'nombre_padre', default='Apoderado')
                apellidos_padre = obtener_campo(fila, 'apellidos_apoderado', 'apellidos_padre', 'apellido_padre', default='')
                telefono_padre = obtener_campo(fila, 'celular', 'telefono', 'whatsapp')
                email_padre = obtener_campo(fila, 'email', 'correo')

                nombres_alumno = obtener_campo(fila, 'nombres_alumno', 'nombre_alumno', 'nombres_estudiante')
                apellidos_alumno = obtener_campo(fila, 'apellidos_alumno', 'apellido_alumno', 'apellidos_estudiante')

                # Soporte para columnas separadas GRADO + SECCION, o columna única GRADO_SECCION
                grado_col = obtener_campo(fila, 'grado_seccion')
                if not grado_col:
                    grado_val = obtener_campo(fila, 'grado', default='Por Asignar')
                    seccion_val = obtener_campo(fila, 'seccion')
                    grado = f"{grado_val} {seccion_val}".strip() if seccion_val else grado_val
                else:
                    grado = grado_col

                mes_ingreso_raw = obtener_campo(fila, 'mes_ingreso', 'mes', default='3')
                # Normalizar: si el valor es '3 - Marzo' extraer el número
                if mes_ingreso_raw and ' - ' in mes_ingreso_raw:
                    mes_ingreso_raw = mes_ingreso_raw.split(' - ')[0].strip()

                if not dni_padre or not nombres_alumno or not apellidos_alumno:
                    errores.append(f'Fila {num_fila}: Datos incompletos (requiere DNI Apoderado, Nombres y Apellidos del Alumno).')
                    continue

                try:
                    mes_ingreso = int(float(mes_ingreso_raw)) if mes_ingreso_raw else 3
                    if mes_ingreso < 1 or mes_ingreso > 12:
                        mes_ingreso = 3
                except ValueError:
                    mes_ingreso = 3

                # 1. get_or_create para el Padre / Apoderado (evita duplicados si tiene varios hijos)
                padre, p_created = Usuario.objects.get_or_create(
                    username=dni_padre,
                    defaults={
                        'first_name': nombres_padre,
                        'last_name': apellidos_padre,
                        'telefono': telefono_padre,
                        'email': email_padre,
                        'es_padre': True,
                    }
                )
                if p_created:
                    padre.set_password(dni_padre)
                    padre.es_padre = True
                    padre.save()
                    padres_creados += 1
                else:
                    padres_existentes += 1
                    # Actualizar campos si antes no estaban completos
                    actualizar = False
                    if not padre.first_name and nombres_padre:
                        padre.first_name = nombres_padre
                        actualizar = True
                    if not padre.last_name and apellidos_padre:
                        padre.last_name = apellidos_padre
                        actualizar = True
                    if not padre.telefono and telefono_padre:
                        padre.telefono = telefono_padre
                        actualizar = True
                    if not padre.es_padre:
                        padre.es_padre = True
                        actualizar = True
                    if actualizar:
                        padre.save()

                # 2. get_or_create para el Alumno
                alumno, a_created = Alumno.objects.get_or_create(
                    padre=padre,
                    nombres=nombres_alumno,
                    apellidos=apellidos_alumno,
                    defaults={
                        'grado': grado,
                        'mes_ingreso': mes_ingreso,
                        'activo': True
                    }
                )

                if a_created:
                    alumnos_creados += 1
                    # 3. Autogenerar cronograma de pensiones si el año escolar está activo
                    if anio_reciente:
                        mes_inicio = max(3, alumno.mes_ingreso)
                        for m in range(mes_inicio, 13):
                            fecha_venc = datetime.date(anio_reciente.anio, m, 28)
                            _, p_gen = PensionMensual.objects.get_or_create(
                                alumno=alumno,
                                anio_academico=anio_reciente,
                                mes=m,
                                defaults={
                                    'monto_deuda': anio_reciente.pension_base,
                                    'fecha_vencimiento': fecha_venc,
                                    'pagado': False
                                }
                            )
                            if p_gen:
                                pensiones_creadas_total += 1
                else:
                    alumnos_existentes += 1

            # Resumen de resultados
            resumen = f"Carga completada: {alumnos_creados} alumno(s) nuevo(s) registrado(s) y {padres_creados} nuevo(s) apoderado(s)."
            if alumnos_existentes > 0 or padres_existentes > 0:
                resumen += f" ({alumnos_existentes} alumnos y {padres_existentes} apoderados ya estaban registrados)."
            if pensiones_creadas_total > 0:
                resumen += f" Se generaron {pensiones_creadas_total} mensualidades para el año {anio_reciente.anio}."

            messages.success(request, resumen)
            if errores:
                messages.warning(request, f"Advertencias en {len(errores)} fila(s): " + "; ".join(errores[:4]))

            return redirect('lista_alumnos')

        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return redirect('carga_masiva_alumnos')

    return render(request, 'alumnos/carga_masiva.html')
