import io
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.urls import reverse
from coordenacao.models import User, Coordenador, Professor, Aluno, Curso, Disciplina, Periodo, Oferta, Matricula, Atividade, Resposta, Frequencia, AlunoFrequencia
from django.core.mail import send_mail
import secrets
import string
import datetime

def generate_password(): 
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(8))

def checkbox_week_days(request):
    result = ''
    try:
        result = result+request.POST['segunda']
    except:
        pass
    try:
        result = result+request.POST['terca']
    except:
        pass
    try:
        result = result+request.POST['quarta']
    except:
        pass
    try:
        result = result+request.POST['quinta']
    except:
        pass
    try:
        result = result+request.POST['sexta']
    except:
        pass
    try:
        result = result+request.POST['sabado']
    except:
        pass
    try:
        result = result+request.POST['domingo']
    except:
        pass
    return result

def download_resposta(request, id_param, id_atividade, pk):
    # this url is for download
    try:
        obj = Resposta.objects.get(pk=pk)
    except Resposta.DoesNotExist as exc:
        return JsonResponse({'status_message': 'No Resource Found'})
    get_binary = obj.arquivo
    if get_binary is None:
        return JsonResponse({'status_message': 'Resource does not contain file'})
    if isinstance(get_binary, memoryview):
        binary_io = io.BytesIO(get_binary.tobytes())
    else:
        binary_io = io.BytesIO(get_binary)
    response = FileResponse(binary_io)
    response['Content-Type'] = 'application/x-binary'
    response['Content-Disposition'] = f'attachment; filename="{obj.atividade} - {obj.aluno.pk}.pdf"'.format(pk)
    return response

def send_email_new_user(email_destinatario, password, user_nome):
    send_mail('SIACA - Sua conta foi criada!', 
    
    f'Olá {user_nome}!\nSua conta do Sistema Acadêmico foi criada, utilize seu CPF e a senha: {password} para fazer login.', 
    
    'mvgp1@aluno.ifal.edu.br',
    [email_destinatario], fail_silently=False)
def index(request):
    '''
    Página de index
    '''
    request.session.flush()
    return render(request, 'coordenacao/login.html', {})

def login(request):
    '''
    Recebe POST com CPF e Senha
    efetua o login
    Retorna para o index caso falhe, ou redireciona para o Home caso tenha sucesso
    user_type:
        1 = Coordenador
        2 = Professor
        3 = Aluno
    '''
    if request.method == 'POST':
        try:
            user = User.objects.get(cpf=request.POST['cpf'])
            print(user)
            if user.password == request.POST['password']:
                # Success Login
                request.session['login_error'] = ""
                request.session['user_id'] = user.cpf
                try:
                    Coordenador.objects.get(user_id=request.session['user_id'])
                    request.session['user_type'] = 1
                except Coordenador.DoesNotExist:
                    try:
                        Professor.objects.get(user_id=request.session['user_id'])
                        request.session['user_type'] = 2
                    except Professor.DoesNotExist:
                        request.session['user_type'] = 3
                return redirect('home')
            else:
                request.session['login_error'] = 'Senha incorreta'
                return redirect(reverse('index'))
        except:
            request.session['login_error'] = 'Usuário não encontrado'
            return redirect(reverse('index'))
    else:
        return redirect(reverse('index'))

def home(request):
    '''
    Página Home
    '''
    # try:
    user_name = User.objects.get(cpf=request.session['user_id']).nome
    request.session['user_name'] = user_name
    atividades=[] 
    if request.session['user_type'] == 1:
        home_name = 'coordenador/home-coordenador'
        ofertas = Oferta.objects.filter(professor=None)
    elif request.session['user_type'] == 2:
        home_name = 'professor/home-professor'
        ofertas = Oferta.objects.filter(professor__pk=request.session['user_id'], periodo__end_date__gte=datetime.date.today())
        atividades = Atividade.objects.filter(oferta__in=ofertas)
        respostas = Resposta.objects.filter(atividade__in=atividades, nota=None)
        atividades_sem_nota = []
        for r in respostas:
            atividades_sem_nota.append(r.atividade.id)
        atividades = Atividade.objects.filter(pk__in=atividades_sem_nota).order_by('entrega_date')

    else:
        home_name = 'aluno/home-aluno'
        matriculas = Matricula.objects.filter(aluno__pk=request.session['user_id'], oferta__periodo__end_date__gte=datetime.date.today())
        ofertas = []
        for m in matriculas:
            ofertas.append(m.oferta)
        atividades = Atividade.objects.filter(oferta__in=ofertas, entrega_date__gte=datetime.date.today())
        respostas = Resposta.objects.filter(atividade__in=atividades)
        atividades_feitas = []
        for r in respostas:
            atividades_feitas.append(r.atividade.id)
        atividades = Atividade.objects.exclude(pk__in=atividades_feitas).order_by('entrega_date')
    print(f'coordenacao/{home_name}.html')
    return render(request, f'coordenacao/{home_name}.html', {'ofertas' : ofertas,
                                                            'atividades' : atividades})
    # except:
    #     return redirect(reverse('index'))

def logout(request):
    '''
    Faz logout, limpa Session
    '''
    request.session.flush()
    return redirect(reverse('index'))

# Aluno
def list_alunos(request):
    '''
    Retorna html com lista de Alunos Cadastrados
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        request.session['aluno_create_error'] = False
        alunos = Aluno.objects.all()
        return render(request, f'coordenacao/coordenador/coordenador-aba-aluno.html', {'alunos':alunos})
    else:
        return redirect(reverse('index'))

def form_aluno(request):
    '''
    Retorna html com formulário de criação de aluno
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        cursos = Curso.objects.filter(created_by=Coordenador.objects.get(user_id=request.session['user_id']))
        periodos = Periodo.objects.all()
        return render(request, f'coordenacao/coordenador/create-aluno.html', {'cursos'   : cursos,
                                                                              'periodos' : periodos})
    else:
        return redirect(reverse('index'))

def create_aluno(request):
    '''
    Retorna html com formulário de criação de aluno
    '''
    if request.method == 'POST' and request.session['user_type'] == 1:
        try:
            user = User.objects.get(cpf=request.POST['cpf'])
            request.session['aluno_create_error'] = True
            return redirect(reverse('form_aluno'))
        except:
            # Gera Senha
            passwrd = generate_password()
            # Cria Usuário
            new_user = User(cpf=request.POST['cpf'], email=request.POST['email'], password=passwrd, nome=request.POST['nome'], telefone=request.POST['telefone'],
                            endereco=request.POST['endereco'], bairro=request.POST['bairro'], cidade=request.POST['cidade'], estado=request.POST['estado'])
            new_user.save()

            # Cria Aluno com novo Usuário
            new_aluno = Aluno(user=new_user, curso_id=request.POST['curso'], periodo_ingresso_id=request.POST['periodo'])
            new_aluno.save()

            # Envia email com senha gerada
            send_email_new_user(request.POST['email'], passwrd, request.POST['nome'])
            return redirect(reverse('alunos'))
    else:
        return redirect(reverse('index'))

# Professor
def list_professores(request):
    '''
    Retorna html com lista de Professores Cadastrados
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        request.session['professor_create_error'] = False
        professores = Professor.objects.all()
        return render(request, f'coordenacao/coordenador/coordenador-aba-professores.html', {'professores':professores})
    else:
        return redirect(reverse('index'))

def form_professor(request):
    '''
    Retorna html com formulário de criação de professores
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        return render(request, f'coordenacao/coordenador/create-professor.html')
    else:
        return redirect(reverse('index'))

def create_professor(request):
    '''
    Retorna html com formulário de criação de professores
    '''
    if request.method == 'POST' and request.session['user_type'] == 1:
        try:
            user = User.objects.get(cpf=request.POST['cpf'])
            request.session['professor_create_error'] = True
            return redirect(reverse('form_professor'))
        except:
            # Gera Senha
            passwrd = generate_password()
            # Cria Usuário
            new_user = User(cpf=request.POST['cpf'], email=request.POST['email'], password=passwrd, nome=request.POST['nome'], telefone=request.POST['telefone'],
                            endereco=request.POST['endereco'], bairro=request.POST['bairro'], cidade=request.POST['cidade'], estado=request.POST['estado'])
            new_user.save()

            # Envia email com senha gerada
            send_email_new_user(request.POST['email'], passwrd, request.POST['nome'])
            
            # Cria Aluno com novo Usuário
            new_professor = Professor(user=new_user, lattes=request.POST['lattes'], area_atuacao=request.POST['atuacao'])
            new_professor.save()
            return redirect(reverse('professores'))            
    else:
        return redirect(reverse('index'))

def list_curso(request):
    '''
    Retorna html com lista de cursos criados pelo usuário coordenador em sessão
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        cursos = Curso.objects.filter(created_by=Coordenador.objects.get(user_id=request.session['user_id']))
        return render(request, f'coordenacao/coordenador/curso-vigentes-coordenador.html', {'cursos':cursos})
    else:
        return redirect(reverse('index'))

def form_curso(request):
    '''
    Retorna html com formulário de criação de curso
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        return render(request, f'coordenacao/coordenador/cadastrar-novo-curso-coordenador.html')
    else:
        return redirect(reverse('index'))

def create_curso(request):
    if request.method == 'POST' and request.session['user_type'] == 1:
        # try:
        file = request.FILES['ementa'].file.getvalue()
        new_curso = Curso(nome=request.POST['nome'], descricao=request.POST['descricao'],
                        periodos=request.POST['periodos'], ementa=file, 
                        created_by=Coordenador.objects.get(pk=request.session['user_id']))
        new_curso.save()
        return redirect(reverse('cursos'))
        # except:
    else:
        return redirect(reverse('index'))

def view_curso(request, id_param):
    '''
    Retorna html com lista de disciplinas do curso
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        curso = get_object_or_404(Curso, pk=id_param)
        disciplinas = Disciplina.objects.filter(curso=curso)
        return render(request, f'coordenacao/coordenador/disciplinas-vigentes-coordenador.html', {'disciplinas' : disciplinas, 
                                                                                                        'curso' : curso})
    else:
        return redirect(reverse('index'))

def form_disciplina(request, id_param):
    '''
    Retorna html com formulário de criação de disciplina
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        return render(request, f'coordenacao/coordenador/cadastrar-nova-disciplina-coordenador.html', {'id_param':id_param})
    else:
        return redirect(reverse('index'))

def create_disciplina(request, id_param):
    if request.method == 'POST' and request.session['user_type'] == 1:
        curso = get_object_or_404(Curso, pk=id_param) 
        file = request.FILES['ementa'].file.getvalue()
        new_disciplina = Disciplina(nome=request.POST['nome'], descricao=request.POST['descricao'], carga_horaria=request.POST['carga_horaria'],
                        periodo=request.POST['periodo'], ementa=file, curso=curso)
        new_disciplina.save()
        return redirect(curso)
    else:
        return redirect(reverse('index'))

def list_periodo(request):
    '''
    Retorna html com lista de cursos
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        periodos = Periodo.objects.all()
        return render(request, f'coordenacao/coordenador/periodos-cadastrados-coordenador.html', {'periodos':periodos})
    else:
        return redirect(reverse('index'))

def form_periodo(request):
    '''
    Retorna html com formulário de criação de periodo
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        return render(request, f'coordenacao/coordenador/cadastrar-periodo.html')
    else:
        return redirect(reverse('index'))

def create_periodo(request):
    if request.method == 'POST' and request.session['user_type'] == 1:
        try:
            periodo = Periodo.objects.get(pk=request.POST['ano']+request.POST['semestre'])
            request.session['periodo_create_error'] = True
            return redirect(reverse('form_periodo'))
        except:
            new_periodo = Periodo(id=request.POST['ano']+request.POST['semestre'], 
                            start_date=request.POST['data_inicio'], end_date=request.POST['data_fim'])
            new_periodo.save()
            return redirect(reverse('periodos')) #get com id como param
    else:
        return redirect(reverse('index'))

def view_periodo(request, id_param):
    '''
    Retorna html com lista de ofertas do periodo
    OBS.: apenas ofertas com disciplinas pertencentes aos cursos criados pelo coordenador
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        periodo = get_object_or_404(Periodo, pk=id_param)
        cursos = Curso.objects.filter(created_by__pk=request.session['user_id'])
        disciplinas = Disciplina.objects.filter(curso__in=cursos)
        ofertas = Oferta.objects.filter(disciplina__in=disciplinas, periodo=periodo)
        return render(request, f'coordenacao/coordenador/visualizar-periodo.html', {'ofertas'     : ofertas,
                                                                                    'periodo'     : periodo})
    else:
        return redirect(reverse('index'))

def form_oferta(request, id_param):
    '''
    Retorna html com lista de ofertas do periodo
    OBS.: apenas ofertas com disciplinas pertencentes aos cursos criados pelo coordenador
    '''
    if request.method == 'GET' and request.session['user_type'] == 1:
        periodo = get_object_or_404(Periodo, pk=id_param)
        cursos = Curso.objects.filter(created_by__pk=request.session['user_id'])
        disciplinas = Disciplina.objects.filter(curso__in=cursos)
        professores = Professor.objects.all()
        return render(request, f'coordenacao/coordenador/cadastrar-oferta.html',   {'professores' : professores,
                                                                                    'disciplinas' : disciplinas,
                                                                                    'periodo'     : periodo})
    else:
        return redirect(reverse('index'))

def create_oferta(request, id_param):
    if request.method == 'POST' and request.session['user_type'] == 1:
        if request.POST['professor'] == "None":
            professor = None
        else:
            professor = Professor.objects.get(pk=request.POST['professor'])
            
        aula_dias = checkbox_week_days(request)
        periodo = get_object_or_404(Periodo, pk=id_param)
        disciplina = get_object_or_404(Disciplina, pk=request.POST['disciplina'])
        new_oferta = Oferta(periodo=periodo,
                            disciplina=disciplina, 
                            professor=professor,
                            capacidade=request.POST['capacidade'],
                            aula_dias=aula_dias, 
                            aula_hora_inicio=request.POST['hora_inicio'],
                            aula_hora_fim=request.POST['hora_fim'])
        new_oferta.save()
        return redirect(periodo)
    else:
        return redirect(reverse('index'))

def view_oferta_matriculados(request, id_param):
    if request.method == 'GET' and request.session['user_type'] == 1:
        matriculas = Matricula.objects.filter(oferta__pk=id_param)
        return render(request, f'coordenacao/coordenador/oferta-matriculas.html', {'matriculas' : matriculas})
    else:
        return redirect(reverse('index'))

def view_perfil(request):
    if request.method == 'GET' and request.session['user_id']:
        try:
            user = User.objects.get(cpf=request.session['user_id'])
            if request.session['user_type'] == 1:
                perfil_name = 'coordenador/perfil-coordenador'
            elif request.session['user_type'] == 2:
                perfil_name = 'professor/perfil-professor'
            else:
                perfil_name = 'aluno/perfil-aluno'
            print(f'coordenacao/{perfil_name}.html')
            return render(request, f'coordenacao/{perfil_name}.html', {'user':user})
        except:
            return redirect(reverse('index'))
    else:
        return redirect(reverse('index'))

def form_editar_perfil(request):
    if request.session['user_id']:
        try:
            user = User.objects.get(cpf=request.session['user_id'])
            return render(request, f'coordenacao/editar-dados.html', {'user':user})
        except:
            return redirect(reverse('index'))
    else:
            return redirect(reverse('index'))

def edit_user(request):
    if request.method == 'POST' and request.session['user_id']:
        try:
            user = User.objects.filter(pk=request.session['user_id']).update(
                nome = request.POST['nome'],
                email = request.POST['email'],
                telefone = request.POST['telefone'],
                endereco = request.POST['endereco'],
                bairro = request.POST['bairro'],
                cidade = request.POST['cidade'],
                estado = request.POST['estado'])
            return redirect(reverse('view_perfil'))
        except:
            return redirect(reverse('index'))
    else:   
        return redirect(reverse('index'))

def edit_password(request):
    if request.method == 'POST' and request.session['user_id']:
        try:
            user = User.objects.get(cpf=request.session['user_id'])
            if request.POST['password'] == user.password:
                user = User.objects.filter(cpf=request.session['user_id']).update(
                    password = request.POST['password2'])
                return redirect(reverse('view_perfil'))
            else:
                return redirect(reverse('form_perfil'))
        except:
            return redirect(reverse('index'))
    else:   
        return redirect(reverse('index'))

def list_ofertas(request):
    if request.method == 'GET' and request.session['user_id']:
        try:
            user = User.objects.get(cpf=request.session['user_id'])
            disciplinas = Disciplina.objects.filter(curso__pk=user.aluno.curso.id)
            ofertas = Oferta.objects.filter(disciplina__in=disciplinas, periodo__pk__gte=user.aluno.periodo_ingresso.id)
            return render(request, f'coordenacao/aluno/matricula.html', {'ofertas' : ofertas})
        except:
            return redirect(reverse('index'))

def create_matricula(request):
    if request.method == 'POST' and request.session['user_id']:
        # try:
            aluno = get_object_or_404(Aluno, pk=request.session['user_id'])
            matriculas = []
            for oferta in request.POST['ofertas']:
                new_matricula = Matricula(aluno=aluno, oferta=oferta)
                new_matricula.save()
                matriculas.append(new_matricula)
            render(request, f'coordenacao/aluno/matricula-realizada.html', {'matriculas' : matriculas})
    else:   
        return redirect(reverse('index'))

def list_alunos_matriculados(request, id_param, id_oferta):
    if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_oferta)
        matriculas = Matricula.objects.filter(oferta=oferta)
        return render(request, f'coordenacao/coordenador/alunos-matriculados.html', {'matriculas' : matriculas,
                                                                                  'oferta' : oferta})
    else:   
        return redirect(reverse('index'))
            
def list_ofertas_matriculadas(request):
    if request.method == 'GET' and request.session['user_id']:
        user = get_object_or_404(User, pk=request.session['user_id'])
        matriculas = Matricula.objects.filter(aluno__pk=user.pk) 
        return render(request, f'coordenacao/aluno/lista-matriculas.html', {'matriculas' : matriculas})
    else:   
        return redirect(reverse('index'))

def list_ofertas_lecionadas(request):
    if request.method == 'GET' and request.session['user_id']:
        user = get_object_or_404(User, pk=request.session['user_id'])
        query = '''SELECT o.id, o.disciplina_id, d.nome, count(distinct m.id) as count_alunos, count(distinct a.id) as count_atividades FROM coordenacao_oferta o
                    LEFT JOIN coordenacao_disciplina d
                    ON o.disciplina_id = d.id
                    LEFT JOIN coordenacao_matricula m
                    ON o.id = m.oferta_id
                    LEFT JOIN coordenacao_atividade a
                    ON o.id = a.oferta_id
                    where o.professor_id=%s
                    group by o.id;
                '''
        ofertas = Oferta.objects.raw(query, [user.pk])
        # ofertas = Oferta.objects.filter(professor__pk=user.pk) 
        return render(request, f'coordenacao/professor/lista-de-disciplinas-professor.html', {'ofertas' : ofertas})
    else:   
        return redirect(reverse('index'))

def view_oferta(request, id_param):
    if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_param)
        atividades = Atividade.objects.filter(oferta=oferta).order_by('-entrega_date') 
        return render(request, f'coordenacao/professor/menu-de-disciplinas-professor.html', {'oferta' : oferta,
                                                                                             'atividades' : atividades,
                                                                                             'count_atividades' : len(atividades)})
    else:   
        return redirect(reverse('index'))

def list_atividades(request, id_param):
    if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_param)
        atividades = Atividade.objects.filter(oferta=oferta).order_by('-entrega_date') 
        return render(request, f'coordenacao/professor/lista-atividades.html', {'oferta' : oferta,
                                                                                'atividades' : atividades})
    else:   
        return redirect(reverse('index'))

def form_atividade(request, id_param):
    if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_param)
        return render(request, f'coordenacao/professor/criar-atividade-professor.html', {'oferta' : oferta})
    else:   
        return redirect(reverse('index'))
            
def create_atividade(request, id_param):
    if request.method == 'POST' and request.session['user_type'] == 2:
        oferta = get_object_or_404(Oferta, pk=id_param) 
        file = request.FILES['arquivo'].file.getvalue()
        new_atividade = Atividade(nome=request.POST['nome'], descricao=request.POST['descricao'],
                        arquivo=file, entrega_date=request.POST['entrega_date'], oferta=oferta)
        new_atividade.save()
        return redirect(new_atividade)
    else:
        return redirect(reverse('index'))

def view_atividade(request, id_param, id_atividade):
    # if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_param)
        atividade = get_object_or_404(Atividade, pk=id_atividade)
        aberta = (atividade.entrega_date >= datetime.date.today())
        if request.session['user_type'] == 2:
            html_name = 'professor/atividade-e-nota'
            respostas = Resposta.objects.filter(atividade=atividade)
        else:
            html_name = 'aluno/atividade-aluno'
            respostas = Resposta.objects.filter(atividade=atividade, aluno__pk=request.session['user_id'])
        return render(request, f'coordenacao/{html_name}.html', {'oferta' : oferta,
                                                                'atividade' : atividade,
                                                                'respostas' : respostas,
                                                                'aberta' : aberta})
    # else:   
    #     return redirect(reverse('index'))

def update_reposta_nota(request, id_param, id_atividade):
    if request.method == 'POST' and request.session['user_type'] == 2:
        oferta = get_object_or_404(Oferta, pk=id_param)
        atividade = get_object_or_404(Atividade, pk=id_atividade) 
        respostas = Resposta.objects.filter(atividade=atividade, nota=None)
        for resposta in respostas:
            try:
                resposta_update = Resposta.objects.filter(pk=resposta.id).update(
                        nota = request.POST[f'{resposta.id}_nota'])
            except:
                pass
        return redirect(atividade)
    else:
        return redirect(reverse('index')) 

def view_oferta_notas(request, id_param):
    if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_param)
        query = '''SELECT m.aluno_id, sum(r.nota) as sum_nota FROM coordenacao_matricula m
                    LEFT JOIN coordenacao_resposta r
                    ON m.aluno_id = r.aluno_id
                    where m.oferta_id=%s
                    group by m.aluno_id;'''
        matriculas = Aluno.objects.raw(query, [oferta.id])
        
        return render(request, f'coordenacao/coordenador/notas-oferta.html', {'oferta' : oferta,
                                                                             'matriculas' : matriculas})
    else:   
        return redirect(reverse('index'))

def create_reposta(request, id_param, id_atividade):
    if request.method == 'POST' and request.session['user_type'] == 3:
        oferta = get_object_or_404(Oferta, pk=id_param)
        atividade = get_object_or_404(Atividade, pk=id_atividade) 
        file = request.FILES['arquivo'].file.getvalue()
        new_resposta = Resposta(atividade=atividade, aluno_id=request.session['user_id'], descricao='',
                        arquivo=file, nota=None)
        new_resposta.save()
        return redirect(atividade)
    else:
        return redirect(reverse('index'))          

def list_frequencias(request, id_param):
    if request.method == 'GET' and request.session['user_id']:
        try:
            oferta = get_object_or_404(Oferta, pk=id_param)
            frequencias = Frequencia.objects.filter(oferta=oferta)
            return render(request, f'coordenacao/aluno/list-frequencias.html', {'oferta' : oferta,
                                                                                'frequencias' : frequencias })
        except:
            return redirect(reverse('index'))

def form_frequencia(request, id_param):
    if request.method == 'GET' and request.session['user_id']:
        oferta = get_object_or_404(Oferta, pk=id_param)
        matriculas = Matricula.objects.filter(oferta=oferta)
        return render(request, f'coordenacao/coordenador/form-frequencia.html', {'oferta' : oferta,
                                                                                 'matriculas' : matriculas})
    else:   
        return redirect(reverse('index'))

def create_frequencia(request, id_param):
    if request.method == 'POST' and request.session['user_type'] == 3:
        oferta = get_object_or_404(Oferta, pk=id_param)

        # Create frequencia
        new_frequencia = Frequencia(aula_date=request.POST['aula_date'], oferta=oferta)
        new_frequencia.save()

        # Save alunos in frequencia
        for aluno in request.POST['alunos']:
            new_freq_aluno = AlunoFrequencia(frequencia=new_frequencia, aluno=aluno)
            new_freq_aluno.save()
            new_freq_aluno = None

        return redirect(reverse('list_frequecias'))
    else:
        return redirect(reverse('index'))   



            
