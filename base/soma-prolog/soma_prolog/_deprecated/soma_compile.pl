% SOMA Compile — CODE-status concepts become executable Python via Janus
%
% The filled partials ARE a valid program in a language defined by OWL.
% Prolog rules decide WHEN to compile and WHEN to run.
% Janus bridges to Python runtime.
% Compilation rules are themselves observable/dogfoodable.
%
% Flow:
%   1. domain_validation_status(Domain, Concept, code) → compilable
%   2. should_compile/2 → Prolog rule says yes
%   3. assemble_program/4 → Prolog gathers partials into program structure
%   4. compile_to_python/3 → generates Python code string from structure
%   5. should_run/2 → Prolog rule says yes (inputs available)
%   6. run_compiled/4 → Janus executes Python, returns result

:- dynamic compiled_program/3.     % compiled_program(Domain, Concept, PythonCode)
:- dynamic compilation_log/4.      % compilation_log(Domain, Concept, Timestamp, Status)
:- dynamic runtime_input/3.        % runtime_input(Domain, Concept, InputDict)
:- dynamic execution_result/4.     % execution_result(Domain, Concept, Timestamp, Result)

% ======================================================================
% WHEN TO COMPILE — Prolog rules
% ======================================================================

% A concept should compile when it reaches CODE status, is a process, and is authorized
should_compile(Domain, Concept) :-
    domain_validation_status(Domain, Concept, code),
    domain_concept(Domain, Concept, process),
    \+ compiled_program(Domain, Concept, _),  % Not already compiled
    is_authorized(Domain, Concept).

% Authorization check — must be explicitly authorized by an agent (human or LLM)
:- dynamic authorized_compilation/3.  % authorized_compilation(Domain, Concept, AuthorizedBy)

is_authorized(Domain, Concept) :-
    authorized_compilation(Domain, Concept, _).

% Authorize compilation — called by an authorized agent
authorize_compilation(Domain, Concept, AuthorizedBy) :-
    domain_concept(Domain, Concept, _),
    assert(authorized_compilation(Domain, Concept, AuthorizedBy)).

% Who authorized this?
who_authorized_compilation(Domain, Concept, Who) :-
    authorized_compilation(Domain, Concept, Who).

% ======================================================================
% ASSEMBLE PROGRAM — Gather filled partials into program structure
% ======================================================================

% Collect the full program structure from domain partials
assemble_program(Domain, Concept, Program) :-
    % Get process-level info
    domain_partial(Domain, Concept, has_inputs, _, resolved(InputsStr)),
    domain_partial(Domain, Concept, has_outputs, _, resolved(OutputsStr)),
    domain_partial(Domain, Concept, has_roles, _, resolved(RolesStr)),
    % Get all steps in order
    findall(
        step(StepName, MethodName, MethodBody, MethodParams),
        (   domain_has_rel(Domain, Concept, has_step, StepConcept),
            domain_partial(Domain, StepConcept, has_method_name, _, resolved(MethodName)),
            domain_partial(Domain, StepConcept, has_method_body, _, resolved(MethodBody)),
            domain_partial(Domain, StepConcept, has_method_parameters, _, resolved(MethodParams)),
            % Extract step name from concept name (ConceptName_Step_X → X)
            atom_string(Concept, ConceptStr),
            atom_string(StepConcept, StepConceptStr),
            string_concat(ConceptStr, "_Step_", PrefixStr),
            string_length(PrefixStr, PrefixLen),
            string_length(StepConceptStr, TotalLen),
            (   TotalLen > PrefixLen
            ->  sub_string(StepConceptStr, PrefixLen, _, 0, StepNameStr),
                atom_string(StepName, StepNameStr)
            ;   StepName = StepConcept
            )
        ),
        Steps
    ),
    Program = program(Concept, InputsStr, OutputsStr, RolesStr, Steps).

% ======================================================================
% COMPILE TO PYTHON — Generate Python code from program structure
% ======================================================================

compile_to_python(Domain, Concept, PythonCode) :-
    should_compile(Domain, Concept),
    assemble_program(Domain, Concept, Program),
    Program = program(Name, InputsStr, OutputsStr, _RolesStr, Steps),
    % Build RenderablePiece classes and MetaStack assembly
    build_piece_classes(Steps, PieceClasses),
    build_stack_assembly(Name, Steps, InputsStr, StackAssembly),
    % Assemble full Python code
    format(atom(PythonCode),
'# Auto-compiled from SOMA domain observations
# Concept: ~w (all partials filled -> CODE)
from pydantic import Field
from pydantic_stack_core.core import RenderablePiece, MetaStack

~w
def ~w(~w):
    """~w — auto-compiled from observations"""
~w
',
        [Name, PieceClasses, Name, InputsStr, Name, StackAssembly]),
    % Store compiled program
    get_time(T),
    assert(compiled_program(Domain, Concept, PythonCode)),
    assert(compilation_log(Domain, Concept, T, compiled)).

% Build RenderablePiece classes from steps
build_piece_classes([], '').
build_piece_classes([step(StepName, _MethodName, MethodBody, MethodParams)|Rest], AllClasses) :-
    % Convert step name to PascalCase class name
    format(atom(ClassName), '~w', [StepName]),
    % Build field declarations from params
    build_fields(MethodParams, FieldLines),
    % Build render method using the method body as logic
    format(atom(ClassDef),
'class ~w(RenderablePiece):
    """~w"""
~w
    def render(self):
        return f"~w"

', [ClassName, StepName, FieldLines, MethodBody]),
    build_piece_classes(Rest, RestClasses),
    format(atom(AllClasses), '~w~w', [ClassDef, RestClasses]).

% Build Pydantic field declarations from comma-separated params
build_fields(ParamStr, FieldLines) :-
    split_string(ParamStr, ",", " ", Params),
    build_field_lines(Params, FieldLines).

build_field_lines([], '').
build_field_lines([P|Rest], AllLines) :-
    format(atom(Line), '    ~w: str = Field(description="~w")~n', [P, P]),
    build_field_lines(Rest, RestLines),
    format(atom(AllLines), '~w~w', [Line, RestLines]).

% Build MetaStack assembly in the main function
build_stack_assembly(Name, Steps, _InputsStr, Assembly) :-
    build_piece_instantiations(Steps, PieceInsts),
    format(atom(Assembly),
'    stack = MetaStack(pieces=[
~w    ], separator="\\n\\n")
    return stack.render()
', [PieceInsts]).

% Build piece instantiation lines
build_piece_instantiations([], '').
build_piece_instantiations([step(StepName, _MN, _MB, MethodParams)|Rest], AllInsts) :-
    format(atom(ClassName), '~w', [StepName]),
    build_kwargs(MethodParams, KwargStr),
    format(atom(Inst), '        ~w(~w),~n', [ClassName, KwargStr]),
    build_piece_instantiations(Rest, RestInsts),
    format(atom(AllInsts), '~w~w', [Inst, RestInsts]).

% Build keyword arguments from params: "x,y" -> "x=x, y=y"
build_kwargs(ParamStr, KwargStr) :-
    split_string(ParamStr, ",", " ", Params),
    build_kwarg_parts(Params, KwargStr).

build_kwarg_parts([], '').
build_kwarg_parts([P], OneKw) :-
    format(atom(OneKw), '~w=~w', [P, P]), !.
build_kwarg_parts([P|Rest], AllKw) :-
    format(atom(Kw), '~w=~w, ', [P, P]),
    build_kwarg_parts(Rest, RestKw),
    format(atom(AllKw), '~w~w', [Kw, RestKw]).

% ======================================================================
% AUTO-COMPILE — compile all ready concepts in a domain
% ======================================================================

auto_compile_domain(Domain, Results) :-
    findall(
        compiled(Concept, Status),
        (   should_compile(Domain, Concept),
            (   compile_to_python(Domain, Concept, _Code)
            ->  Status = success
            ;   Status = failed
            )
        ),
        Results
    ).

% ======================================================================
% WHEN TO RUN — Prolog rules
% ======================================================================

% A compiled program should run when runtime inputs are available
should_run(Domain, Concept) :-
    compiled_program(Domain, Concept, _),
    runtime_input(Domain, Concept, _).

% Provide runtime inputs for a concept
provide_inputs(Domain, Concept, InputDict) :-
    assert(runtime_input(Domain, Concept, InputDict)).

% ======================================================================
% RUN COMPILED — Execute Python via Janus
% ======================================================================

run_compiled(Domain, Concept, InputDict, Result) :-
    compiled_program(Domain, Concept, PythonCode),
    % Execute via Janus: define the functions, then call the main one
    atom_string(Concept, ConceptStr),
    % Build the call with inputs
    format(atom(ExecCode),
        '~w\nresult = ~w(**~w)\nprint(result)',
        [PythonCode, ConceptStr, InputDict]),
    % Try to execute
    get_time(T),
    (   catch(
            (   janus:py_call(exec(ExecCode), none),
                Result = executed(ConceptStr)
            ),
            Error,
            (   term_to_atom(Error, ErrorAtom),
                Result = error(ErrorAtom)
            )
        )
    ->  true
    ;   Result = error(unknown)
    ),
    assert(execution_result(Domain, Concept, T, Result)).

% ======================================================================
% VIEW COMPILED CODE — inspect what was generated
% ======================================================================

get_compiled_code(Domain, Concept, Code) :-
    compiled_program(Domain, Concept, Code).

get_compiled_code_str(Domain, Concept, Str) :-
    (   compiled_program(Domain, Concept, Code)
    ->  format(atom(Str), 'COMPILED: ~w in ~w~n~n~w', [Concept, Domain, Code])
    ;   format(atom(Str), 'NOT COMPILED: ~w in ~w', [Concept, Domain])
    ).

% ======================================================================
% JANUS WRAPPERS
% ======================================================================

compile_domain_str(Domain, Str) :-
    auto_compile_domain(Domain, Results),
    length(Results, N),
    with_output_to(atom(Str),
        (   format('Compiled ~w concepts in ~w:~n', [N, Domain]),
            forall(member(compiled(C, S), Results),
                format('  ~w: ~w~n', [C, S])
            )
        )).

% ======================================================================
% TESTS
% ======================================================================

% Test: should_compile requires CODE + authorization
test_should_compile :-
    register_domain(test_comp_dom, 'Test'),
    domain_create_partials(test_comp_dom, test_compilable, process),
    % Not compilable yet (soup)
    \+ should_compile(test_comp_dom, test_compilable),
    % Fill all partials
    domain_resolve_partial(test_comp_dom, test_compilable, has_steps, 'step_a'),
    domain_resolve_partial(test_comp_dom, test_compilable, has_roles, 'worker'),
    domain_resolve_partial(test_comp_dom, test_compilable, has_inputs, 'x'),
    domain_resolve_partial(test_comp_dom, test_compilable, has_outputs, 'y'),
    % CODE but NOT authorized — should NOT compile
    \+ should_compile(test_comp_dom, test_compilable),
    % Authorize it
    authorize_compilation(test_comp_dom, test_compilable, isaac),
    % Now compilable
    should_compile(test_comp_dom, test_compilable),
    % Clean up
    retractall(domain_registered(test_comp_dom, _)),
    retractall(domain_concept(test_comp_dom, _, _)),
    retractall(domain_partial(test_comp_dom, _, _, _, _)),
    retractall(domain_has_rel(test_comp_dom, _, _, _)),
    retractall(domain_heal_log(test_comp_dom, _, _, _, _)),
    retractall(authorized_compilation(test_comp_dom, _, _)).

% Test: compile generates Python code from filled partials
test_compile_generates_python :-
    register_domain(test_pydom, 'Test'),
    % Create process with all partials filled
    domain_create_partials(test_pydom, test_py_proc, process),
    domain_resolve_partial(test_pydom, test_py_proc, has_steps, 'do_thing'),
    domain_resolve_partial(test_pydom, test_py_proc, has_roles, 'agent'),
    domain_resolve_partial(test_pydom, test_py_proc, has_inputs, 'x,y'),
    domain_resolve_partial(test_pydom, test_py_proc, has_outputs, 'result'),
    authorize_compilation(test_pydom, test_py_proc, soma_agent),
    % Create a step
    domain_create_partials(test_pydom, 'test_py_proc_Step_do_thing', template_method),
    assert(domain_has_rel(test_pydom, test_py_proc, has_step, 'test_py_proc_Step_do_thing')),
    domain_resolve_partial(test_pydom, 'test_py_proc_Step_do_thing', has_method_name, do_the_thing),
    domain_resolve_partial(test_pydom, 'test_py_proc_Step_do_thing', has_method_body, 'combine x and y'),
    domain_resolve_partial(test_pydom, 'test_py_proc_Step_do_thing', has_method_parameters, 'x,y'),
    % Compile
    compile_to_python(test_pydom, test_py_proc, Code),
    % Code should contain MetaStack, the class, and the render logic
    sub_atom(Code, _, _, _, 'MetaStack'),
    sub_atom(Code, _, _, _, 'RenderablePiece'),
    sub_atom(Code, _, _, _, 'combine x and y'),
    % Should be stored
    compiled_program(test_pydom, test_py_proc, _),
    % Clean up
    retractall(domain_registered(test_pydom, _)),
    retractall(domain_concept(test_pydom, _, _)),
    retractall(domain_partial(test_pydom, _, _, _, _)),
    retractall(domain_has_rel(test_pydom, _, _, _)),
    retractall(domain_heal_log(test_pydom, _, _, _, _)),
    retractall(compiled_program(test_pydom, _, _)),
    retractall(compilation_log(test_pydom, _, _, _)),
    retractall(authorized_compilation(test_pydom, _, _)).

% Test: auto_compile_domain finds and compiles all ready concepts
test_auto_compile :-
    register_domain(test_auto_dom, 'Test'),
    domain_create_partials(test_auto_dom, auto_proc, process),
    domain_resolve_partial(test_auto_dom, auto_proc, has_steps, 's1'),
    domain_resolve_partial(test_auto_dom, auto_proc, has_roles, 'r'),
    domain_resolve_partial(test_auto_dom, auto_proc, has_inputs, 'i'),
    domain_resolve_partial(test_auto_dom, auto_proc, has_outputs, 'o'),
    domain_create_partials(test_auto_dom, 'auto_proc_Step_s1', template_method),
    assert(domain_has_rel(test_auto_dom, auto_proc, has_step, 'auto_proc_Step_s1')),
    domain_resolve_partial(test_auto_dom, 'auto_proc_Step_s1', has_method_name, do_s1),
    domain_resolve_partial(test_auto_dom, 'auto_proc_Step_s1', has_method_body, 'do something'),
    domain_resolve_partial(test_auto_dom, 'auto_proc_Step_s1', has_method_parameters, 'i'),
    authorize_compilation(test_auto_dom, auto_proc, isaac),
    % Auto compile
    auto_compile_domain(test_auto_dom, Results),
    Results \= [],
    member(compiled(auto_proc, success), Results),
    % Clean up
    retractall(domain_registered(test_auto_dom, _)),
    retractall(domain_concept(test_auto_dom, _, _)),
    retractall(domain_partial(test_auto_dom, _, _, _, _)),
    retractall(domain_has_rel(test_auto_dom, _, _, _)),
    retractall(domain_heal_log(test_auto_dom, _, _, _, _)),
    retractall(compiled_program(test_auto_dom, _, _)),
    retractall(compilation_log(test_auto_dom, _, _, _)),
    retractall(authorized_compilation(test_auto_dom, _, _)).

% Test: get_compiled_code retrieves stored code
test_get_compiled :-
    assert(compiled_program(test_get_dom, test_get_proc, 'print("hello")')),
    get_compiled_code(test_get_dom, test_get_proc, Code),
    Code = 'print("hello")',
    retract(compiled_program(test_get_dom, test_get_proc, _)).
