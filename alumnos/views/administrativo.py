"""Vistas del panel administrativo (personal del colegio)."""
import json
import datetime

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse

from usuarios.models import Usuario
from alumnos.models import Alumno
from pagos.models import AnioAcademico, PensionMensual
from pagos.views import is_admin
from alumnos.forms import GRADOS_CHOICES, SECCIONES_CHOICES, MESES_CHOICES

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    openpyxl = None


def get_filter_options(request):
    """Obtiene las opciones de filtro basadas en el año escolar seleccionado."""
    # Determinar año escolar
    anio_param = request.GET.get('anio')
    anios = AnioAcademico.objects.order_by('-anio')
    
    if anio_param == 'todos':
        anio_seleccionado = None
        anio_label = 'Todos los años'
    elif anio_param and str(anio_param).isdigit():
        anio_id = int(anio_param)
        if anios.filter(id=anio_id).exists():
            anio_seleccionado = anio_id
            anio_obj = anios.get(id=anio_id)
            anio_label = f"Año {anio_obj.anio}"
        else:
            anio_seleccionado = None
            anio_label = 'Todos los años'
    else:
        # Por defecto: año más reciente
        anio_seleccionado = anios.first().id if anios.exists() else None
        anio_obj = anios.first() if anios.exists() else None
        anio_label = f"Año {anio_obj.anio}" if anio_obj else 'Todos los años'

    # Obtener alumnos filtrados
    alumnos = Alumno.objects.select_related('padre')
    
    if anio_seleccionado is not None:
        alumnos = alumnos.filter(grado__startswith='')  # Todos, luego filtramos por año
        # Filtrar por año: los grados que tienen alumnos en este año
        # Extraer el grado base (sin sección) para filtrar
        grades_in_year = set()
        for a in alumnos:
            # El grado tiene formato "3° Primaria - A", tomamos la parte antes del espacio final
            parts = a.grado.rsplit(' ', 1)
            grade_base = parts[0] if len(parts) == 2 else a.grado
            grades_in_year.add(grade_base)
    else:
        grades_in_year = None

    # Aplicar búsqueda y filtros adicionales
    q = request.GET.get('q', '').strip()
    grado_sel = request.GET.get('grado', '').strip()
    seccion_sel = request.GET.get('seccion', '').strip()

    if q:
        alumnos = alumnos.filter(
            Q(nombres__icontains=q) | Q(apellidos__icontains=q) |
            Q(padre__username__icontains=q) |
            Q(padre__first_name__icontains=q) | Q(padre__last_name__icontains=q)
        )

    # Filtrar por grado (solo si hay año seleccionado, para limitar las opciones)
    if grado_sel and anio_seleccionado is not None:
        # El grado completo incluye la sección, así que filtramos que empiece con el nivel
        # Ej: "3° Primaria" debe aparecer en "3° Primaria - A"
        alumnos = alumnos.filter(grado__startswith=grado_sel + ' ')
    elif grado_sel and anio_seleccionado is None:
        # Sin año: mostrar alumnos cuyo grado empieza así
        alumnos = alumnos.filter(grado__startswith=grado_sel + ' ')

    # Filtrar por sección (solo si hay año y grado seleccionados)
    if seccion_sel and anio_seleccionado is not None and grado_sel:
        # La sección es la última parte después del espacio final
        alumnos = alumnos.filter(grado__endswith=' ' + seccion_sel)

    # Calcular opciones de grado y sección basadas en alumnos visibles
    # Para el año y grado seleccionados
    grades_options = []
    secciones_options = []
    
    # Obtener todos los grados únicos de la BD para el select general
    all_grades = Alumno.objects.exclude(grado='').order_by('grado').values_list('grado', flat=True).distinct()
    
    # Si hay año seleccionado, filtrar grades a los que hay alumnos en ese año
    if anio_seleccionado is not None:
        grades_filtered = []
        for g in all_grades:
            # Verificar si este grado tiene alumnos en el año seleccionado
            has_students = Alumno.objects.filter(grado=g, padre__isnull=False).exists()
            # Verificar más Specifically: tener alumnos con este grado en el año
            if has_students:
                grades_filtered.append(g)
        grades_options = grades_filtered
    else:
        grades_options = list(all_grades)

    # Obtener secciones únicas
    all_sections = Alumno.objects.exclude(grado='').values_list('grado', flat=True).distinct()
    section_vals = set()
    for g in all_sections:
        parts = g.rsplit(' ', 1)
        if len(parts) == 2:
            section_vals.add(parts[1])
        else:
            # Grado sin sección definida
            pass
    secciones_options = sorted(list(section_vals))

    # Si hay año y grado seleccionados, filtrar secciones realmente disponibles
    if anio_seleccionado is not None and grado_sel:
        # Buscar secciones que aparecen en alumnos con ese grado en el año
        grades_with_section = Alumno.objects.filter(
           grado__startswith=grado_sel + ' '
        ).values_list('grado', flat=True).distinct()
        sections_from_db = set()
        for g in grades_with_section:
            parts = g.rsplit(' ', 1)
            if len(parts) == 2:
                sections_from_db.add(parts[1])
        secciones_options = sorted(list(sections_from_db))
    elif anio_seleccionado is not None:
        # Solo por año: grades ya vienen de grades_options, secciones todas las únicas
        pass

    # Agrupar por salón (grado + sección) los alumnos filtrados
    alumnos = alumnos if alumnos is not None else Alumno.objects.none()
    salones = {}
    for a in alumnos.order_by('grado', 'apellidos', 'nombres'):
        grado = a.grado
        if grado not in salones:
            salones[grado] = []
        salones[grado].append(a)
    
    # Formato lista para el template (lista de dicts, no diccionario anidado)
    grupos_list = []
    for grado, lista in sorted(salones.items()):
        partes = grado.rsplit(' ', 1)
        grupos_list.append({
            'grado': grado,
            'nivel': partes[0] if len(partes) == 2 else grado,
            'seccion': partes[1] if len(partes) == 2 else '',
            'alumnos': lista,
        })
    
    # Estado actual de los filtros
    hay_filtros = bool(q or grado_sel or seccion_sel)

    context = {
        'anio_seleccionado': anio_seleccionado,
        'anio_label': anio_label,
        'anios': anios,
        'alumnos': alumnos,  # Ya filtrados
        'q': q,
        'grado_sel': grado_sel,
        'seccion_sel': seccion_sel,
        'niveles': sorted(grades_options),
        'secciones': sorted(secciones_options),
        'hay_filtros': hay_filtros,
        'total_alumnos': alumnos.count(),
        'grupos': grupos_list,  # Lista lista para el template
    }
    return context


@login_required
@user_passes_test(is_admin)
def lista_alumnos(request):
    """Lista de alumnos con filtros interactivos:
    - Año escolar (por defecto el más reciente)
    - Búsqueda por nombre, apellido o documento
    - Filtro por grado (dependiente del año)
    - Filtro por sección (dependiente del año y grado)
    Los resultados se agrupan por salón (grado + sección)."""
    context = get_filter_options(request)
    context['grupos'] = {}
    context['total_alumnos'] = context['total_alumnos'] or 0
    
    # Agrupar por salón (grado + sección) los alumnos filtrados
    alumnos = context.get('alumnos', Alumno.objects.none())
    
    salones = {}
    for a in alumnos.order_by('grado', 'apellidos', 'nombres'):
        grado = a.grado
        if grado not in salones:
            salones[grado] = []
        salones[grado].append(a)
    
    # Formato para el template
    for grado, lista in sorted(salones.items()):
        partes = grado.rsplit(' ', 1)
        nivel = partes[0] if len(partes) == 2 else grado
        seccion = partes[1] if len(partes) == 2 else ''
        context['grupos'][grado] = {
            'nivel': nivel,
            'seccion': seccion,
            'alumnos': lista,
        }
    
    return render(request, 'administrador/alumnos_lista.html', context)


# ── Vistas de gestión de alumnos ─────────────────────────────────

@login_required
@user_passes_test(is_admin)
def crear_alumno(request):
    """Registra un alumno nuevo."""
    if request.method == 'POST':
        # Obtener datos del formulario
        padre_id = request.POST.get('padre_id', '').strip()
        dni_nuevo = request.POST.get('dni_nuevo', '').strip()
        nom_nuevo = request.POST.get('nuevo_nombres', '').strip()
        ape_nuevo = request.POST.get('nuevo_apellidos', '').strip()
        cel_nuevo = request.POST.get('nuevo_celular', '').strip()
        email_nuevo = request.POST.get('nuevo_email', '').strip()
        
        nombres = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        grado_niv = request.POST.get('grado_nivel', '').strip()
        seccion = request.POST.get('seccion', '').strip()
        mes_raw = request.POST.get('mes_ingreso', '3').strip()
        activo = request.POST.get('activo') == 'on'
        
        errores = {}
        padre = None
        
        # Resolver apoderado
        if padre_id:
            try:
                padre = Usuario.objects.get(pk=int(padre_id), es_padre=True)
            except (Usuario.DoesNotExist, ValueError):
                errores['apoderado'] = 'El apoderado seleccionado no existe.'
        elif dni_nuevo:
            if not nom_nuevo:
                errores['nuevo_nombres'] = 'Ingresa el nombre del apoderado.'
            if not ape_nuevo:
                errores['nuevo_apellidos'] = 'Ingresa los apellidos del apoderado.'
            if not errores:
                if Usuario.objects.filter(username=dni_nuevo).exists():
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
        
        # Validar alumno
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
            if anio_reciente:
                for mes in range(max(3, alumno.mes_ingreso), 13):
                    fecha_venc = datetime.date(anio_reciente.anio, mes, 28)
                    PensionMensual.objects.get_or_create(
                        alumno=alumno, anio_academico=anio_reciente, mes=mes,
                        defaults={'monto_deuda': anio_reciente.pension_base,
                                  'fecha_vencimiento': fecha_venc, 'pagado': False}
                    )
            messages.success(request, f'Alumno {alumno} registrado correctamente.')
            return redirect('lista_alumnos')
        
        # Re-renderizar con errores
        return render(request, 'administrador/alumnos_crear.html', {
            'errores': errores,
            'post_data': request.POST,
            'padre_encontrado': padre,
        })
    
    return render(request, 'administrador/alumnos_crear.html', {})


@login_required
@user_passes_test(is_admin)
def editar_alumno(request, id):
    alumno = get_object_or_404(Alumno, id=id)
    partes_grado = alumno.grado.rsplit(' ', 1)
    grado_actual = partes_grado[0] if len(partes_grado) > 1 else alumno.grado
    seccion_actual = partes_grado[1] if len(partes_grado) > 1 and len(partes_grado[1]) == 1 else ''
    
    errores = {}
    if request.method == 'POST':
        nombres = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        grado_niv = request.POST.get('grado_nivel', '').strip()
        seccion = request.POST.get('seccion', '').strip()
        mes_raw = request.POST.get('mes_ingreso', '3').strip()
        activo = request.POST.get('activo') == 'on'
        
        if not nombres: errores['nombres'] = 'Campo requerido.'
        if not apellidos: errores['apellidos'] = 'Campo requerido.'
        if not grado_niv: errores['grado_nivel'] = 'Selecciona el grado.'
        if not seccion: errores['seccion'] = 'Selecciona la sección.'
        
        if not errores:
            alumno.nombres = nombres
            alumno.apellidos = apellidos
            alumno.grado = f"{grado_niv} {seccion}".strip()
            alumno.mes_ingreso = int(mes_raw) if mes_raw.isdigit() else 3
            alumno.activo = activo
            alumno.save()
            messages.success(request, f'Datos de {alumno} actualizados correctamente.')
            return redirect('lista_alumnos')
        
        grado_actual = grado_niv
        seccion_actual = seccion
    
    return render(request, 'administrador/alumnos_editar.html', {
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
def descargar_plantilla_excel(request):
    """Genera y descarga un archivo Excel (.xlsx) con columnas GRADO y SECCION estandarizadas."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    
    GRADOS = [
        "3 años Inicial", "4 años Inicial", "5 años Inicial",
        "1ro Primaria", "2do Primaria", "3ro Primaria", "4to Primaria", "5to Primaria", "6to Primaria",
        "1ro Secundaria", "2do Secundaria", "3ro Secundaria", "4to Secundaria", "5to Secundaria",
    ]
    SECCIONES = ["A", "B", "C", "D", "E"]
    MESES = [
        "1 - Enero", "2 - Febrero", "3 - Marzo", "4 - Abril",
        "5 - Mayo", "6 - Junio", "7 - Julio", "8 - Agosto",
        "9 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre",
    ]
    
    wb = openpyxl.Workbook()
    ws_ref = wb.create_sheet("_Listas")
    ws_ref.sheet_state = 'hidden'
    ws_ref['A1'] = 'GRADOS'; ws_ref['B1'] = 'SECCIONES'; ws_ref['C1'] = 'MESES'
    for i, g in enumerate(GRADOS, start=2): ws_ref.cell(row=i, column=1, value=g)
    for i, s in enumerate(SECCIONES, start=2): ws_ref.cell(row=i, column=2, value=s)
    for i, m in enumerate(MESES, start=2): ws_ref.cell(row=i, column=3, value=m)
    
    ws_guia = wb.create_sheet("📋 Guía de Valores")
    ws_guia['A1'] = "Guía de valores estandarizados para la plantilla"
    ws_guia['A1'].font = Font(name="Calibri", size=13, bold=True, color="14532D")
    ws_guia.merge_cells('A1:D1')
    
    headers_guia = ["GRADO (columna H)", "SECCION (columna I)", "MES_INGRESO (columna J)", "Nota"]
    for c, h in enumerate(headers_guia, start=1):
        cell = ws_guia.cell(row=3, column=c, value=h)
        cell.fill = PatternFill(start_color="15803D", end_color="15803D", fill_type="solid")
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")
    
    for row in range(max(len(GRADOS), len(SECCIONES), len(MESES))):
        g = GRADOS[row] if row < len(GRADOS) else ""
        s = SECCIONES[row] if row < len(SECCIONES) else ""
        m = MESES[row] if row < len(MESES) else ""
        for c, v in enumerate([g, s, m, ""], start=1):
            ws_guia.cell(row=row+4, column=c, value=v)
    
    for col_idx in range(1, 5):
        ws_guia.column_dimensions[get_column_letter(col_idx)].width = 30
    
    ws = wb.worksheets[0]
    ws.title = "Registro_Alumnos"
    
    headers = ["DNI_APODERADO", "NOMBRES_APODERADO", "APELLIDOS_APODERADO", 
               "CELULAR_APODERADO", "EMAIL_APODERADO", "NOMBRES_ALUMNO", 
               "APELLIDOS_ALUMNO", "GRADO", "SECCION", "MES_INGRESO"]
    
    header_fill = PatternFill(start_color="14532D", end_color="14532D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    ws['A1'] = "DATOS DEL APODERADO"
    ws.merge_cells('A1:E1')
    ws['A1'].fill = header_fill; ws['A1'].font = header_font; ws['A1'].alignment = header_align
    
    ws['F1'] = "DATOS DEL ALUMNO"
    ws.merge_cells('F1:G1')
    ws['F1'].fill = PatternFill(start_color="166534", end_color="166534", fill_type="solid")
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
    
    header_fill2 = PatternFill(start_color="22C55E", end_color="22C55E", fill_type="solid")
    header_font2 = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.row_dimensions[2].height = 30
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=col_idx, value=h)
        cell.fill = header_fill2; cell.font = header_font2; cell.alignment = header_align
    
    ws.row_dimensions[1].height = 22
    
    filas_ejemplo = [
        ["45892134", "Juan Carlos", "Mendoza Flores", "987654321", "juan.mendoza@email.com", "Lucas", "Mendoza Quispe", "3ro Primaria", "A", 3],
        ["45892134", "Juan Carlos", "Mendoza Flores", "987654321", "juan.mendoza@email.com", "Sofia", "Mendoza Quispe", "5to Primaria", "B", 3],
        ["71234567", "Maria Elena", "Castro Lopez", "912345678", "maria.castro@email.com", "Mateo", "Ramos Castro", "1ro Secundaria", "B", 3],
        ["40987654", "Pedro Antonio", "Salas Gutierrez", "945612378", "pedro.salas@email.com", "Valeria", "Salas Vega", "2do Primaria", "A", 3],
        ["40987654", "Pedro Antonio", "Salas Gutierrez", "945612378", "pedro.salas@email.com", "Joaquin", "Salas Vega", "6to Primaria", "A", 3],
    ]
    row_fill_alt = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
    data_font = Font(name="Calibri", size=10)
    for i, fila in enumerate(filas_ejemplo):
        r = i + 3
        for col_idx, val in enumerate(fila, start=1):
            cell = ws.cell(row=r, column=col_idx, value=val)
            cell.font = data_font
            if i % 2 == 0: cell.fill = row_fill_alt
    
    n_grados = len(GRADOS) + 1
    n_sec = len(SECCIONES) + 1
    n_meses = len(MESES) + 1
    
    dv_grado = DataValidation(type="list", formula1=f"'_Listas'!$A$2:$A${n_grados}", allow_blank=True,
                              showErrorMessage=True, errorTitle="Grado inválido", error="Selecciona un grado de la lista.")
    dv_grado.sqref = "H3:H200"
    ws.add_data_validation(dv_grado)
    
    dv_sec = DataValidation(type="list", formula1=f"'_Listas'!$B$2:$B${n_sec}", allow_blank=True,
                            showErrorMessage=True, errorTitle="Sección inválida", error="Selecciona una sección (A-E).")
    dv_sec.sqref = "I3:I200"
    ws.add_data_validation(dv_sec)
    
    dv_mes = DataValidation(type="list", formula1=f"'_Listas'!$C$2:$C${n_meses}", allow_blank=True,
                            showErrorMessage=True, errorTitle="Mes inválido", error="Selecciona el mes de ingreso.")
    dv_mes.sqref = "J3:J200"
    ws.add_data_validation(dv_mes)
    
    anchos = [16, 20, 22, 16, 28, 18, 22, 20, 10, 20]
    for idx, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ancho
    
    ws.freeze_panes = 'A3'
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
    """Procesa la carga masiva desde un archivo Excel o CSV."""
    import openpyxl
    import csv
    import datetime
    
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, 'Por favor, selecciona un archivo Excel (.xlsx) o CSV.')
            return redirect('carga_masiva_alumnos')
        
        nombre = archivo.name.lower()
        if not (nombre.endswith('.xlsx') or nombre.endswith('.xls') or nombre.endswith('.csv')):
            messages.error(request, 'Formato no soportado. Debe ser .xlsx, .xls o .csv.')
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
                decoded_file = archivo.read().decode('utf-8-sig').splitlines()
                reader = csv.DictReader(decoded_file)
                for row in reader:
                    filas_datos.append({k.strip().lower(): v for k, v in row.items() if k})
            
            def obtener_campo(fila_dict, *claves_posibles, default=''):
                for clave in claves_posibles:
                    for k, v in fila_dict.items():
                        if clave in k.lower():
                            if v is not None: return str(v).strip()
                return default
            
            anio_reciente = AnioAcademico.objects.order_by('-anio').first()
            padres_creados = 0
            alumnos_creados = 0
            errores = []
            
            for num_fila, fila in enumerate(filas_datos, start=2):
                dni_padre = obtener_campo(fila, 'dni_apoderado', 'dni_padre', 'doc', 'dni', 'apoderado')
                nombres_padre = obtener_campo(fila, 'nombres_apoderado', 'nombres_padre', 'nombre_padre', default='Apoderado')
                apellidos_padre = obtener_campo(fila, 'apellidos_apoderado', 'apellidos_padre', 'apellido_padre', default='')
                telefono_padre = obtener_campo(fila, 'celular', 'telefono', 'whatsapp')
                email_padre = obtener_campo(fila, 'email', 'correo')
                
                nombres_alumno = obtener_campo(fila, 'nombres_alumno', 'nombre_alumno', 'nombres_estudiante')
                apellidos_alumno = obtener_campo(fila, 'apellidos_alumno', 'apellido_alumno', 'apellidos_estudiante')
                
                grado_col = obtener_campo(fila, 'grado_seccion')
                if not grado_col:
                    grado_val = obtener_campo(fila, 'grado', default='Por Asignar')
                    seccion_val = obtener_campo(fila, 'seccion')
                    grado = f"{grado_val} {seccion_val}".strip() if seccion_val else grado_val
                else:
                    grado = grado_col
                
                mes_ingreso_raw = obtener_campo(fila, 'mes_ingreso', 'mes', default='3')
                if mes_ingreso_raw and ' - ' in mes_ingreso_raw:
                    mes_ingreso_raw = mes_ingreso_raw.split(' - ')[0].strip()
                
                if not dni_padre or not nombres_alumno or not apellidos_alumno:
                    errores.append(f'Fila {num_fila}: Datos incompletos.')
                    continue
                
                try:
                    mes_ingreso = int(float(mes_ingreso_raw)) if mes_ingreso_raw else 3
                    if mes_ingreso < 1 or mes_ingreso > 12: mes_ingreso = 3
                except ValueError:
                    mes_ingreso = 3
                
                # Padre
                padre, p_created = Usuario.objects.get_or_create(
                    username=dni_padre,
                    defaults={'first_name': nombres_padre, 'last_name': apellidos_padre,
                              'telefono': telefono_padre, 'email': email_padre, 'es_padre': True}
                )
                if p_created:
                    padre.set_password(dni_padre)
                    padre.es_padre = True
                    padre.save()
                    padres_creados += 1
                else:
                    if not padre.first_name and nombres_padre: padre.first_name = nombres_padre
                    if not padre.last_name and apellidos_padre: padre.last_name = apellidos_padre
                    if not padre.telefono and telefono_padre: padre.telefono = telefono_padre
                    if not padre.es_padre: padre.es_padre = True
                    padre.save()
                
                # Alumno
                alumno, a_created = Alumno.objects.get_or_create(
                    padre=padre, nombres=nombres_alumno, apellidos=apellidos_alumno,
                    defaults={'grado': grado, 'mes_ingreso': mes_ingreso, 'activo': True}
                )
                if a_created:
                    alumnos_creados += 1
                    if anio_reciente:
                        for m in range(max(3, alumno.mes_ingreso), 13):
                            fecha_venc = datetime.date(anio_reciente.anio, m, 28)
                            PensionMensual.objects.get_or_create(
                                alumno=alumno, anio_academico=anio_reciente, mes=m,
                                defaults={'monto_deuda': anio_reciente.pension_base,
                                          'fecha_vencimiento': fecha_venc, 'pagado': False}
                            )
                else:
                    if not alumno.activo: alumno.activo = True; alumno.save()
            
            resumen = f"Carga completada: {alumnos_creados} alumno(s) nuevo(s) y {padres_creados} apoderado(s) nuevo(s)."
            messages.success(request, resumen)
            if errores:
                messages.warning(request, f"Advertencias en {len(errores)} fila(s): " + "; ".join(errores[:4]))
            return redirect('lista_alumnos')
        
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return redirect('carga_masiva_alumnos')
    
    return render(request, 'administrador/alumnos_carga_masiva.html')


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