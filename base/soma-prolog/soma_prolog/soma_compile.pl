% SOMA Compile — Universal version
%
% When a concept's partials are all resolved (status == code) AND the concept
% is authorized, compile_to_python/2 walks the filled partial structure and
% emits a Python source string using RenderablePiece / MetaStack from
% pydantic_stack_core. run_compiled/3 executes the emitted code via janus
% py_call(exec, none).
%
% The codegen works for ANY concept whose filled partials match the
% expected shape (has_inputs, has_outputs, has_roles, and one or more
% has_step sub-concepts whose own partials contain has_method_name,
% has_method_body, has_method_parameters). The concept's type name is
% not inspected — only the structural shape of its filled partials.

:- dynamic compiled_program/2.      % compiled_program(Concept, PythonCode)
:- dynamic compilation_log/3.       % compilation_log(Concept, Timestamp, Status)
:- dynamic runtime_input/2.         % runtime_input(Concept, InputDict)
:- dynamic execution_result/3.      % execution_result(Concept, Timestamp, Result)
:- dynamic authorized_compilation/2. % authorized_compilation(Concept, AuthorizedBy)

% ======================================================================
% AUTHORIZATION
% ======================================================================

authorize_compilation(Concept, AuthorizedBy) :-
    concept_type(Concept, _),
    assert(authorized_compilation(Concept, AuthorizedBy)).

is_authorized(Concept) :-
    authorized_compilation(Concept, _).

who_authorized_compilation(Concept, Who) :-
    authorized_compilation(Concept, Who).

% ======================================================================
% SHOULD COMPILE — triggers when concept is at CODE status + authorized
% ======================================================================

should_compile(Concept) :-
    deduce_validation_status(Concept, code),
    \+ compiled_program(Concept, _),
    is_authorized(Concept).

% ======================================================================
% ASSEMBLE PROGRAM — gather filled partials into a structure
%
% Universal: walks the concept's has_rel chain to find step sub-concepts,
% pulls their filled method_name/body/parameters. Also pulls the concept's
% own has_inputs/has_outputs/has_roles if present.
% ======================================================================

assemble_program(Concept, Program) :-
    % Pull the concept's own filled partials (optional — missing = '')
    (   has_rel(Concept, has_inputs, InputsStr) ; InputsStr = '' ), !,
    (   has_rel(Concept, has_outputs, OutputsStr) ; OutputsStr = '' ), !,
    (   has_rel(Concept, has_roles, RolesStr) ; RolesStr = '' ), !,
    % Walk step sub-concepts reachable via has_steps -> has_step*
    findall(
        step(StepName, MethodBody, MethodParams),
        (   has_rel(Concept, has_steps, SeqLink),
            has_rel(SeqLink, has_step, StepConcept),
            has_rel(StepConcept, has_method_name, StepName),
            has_rel(StepConcept, has_method_body, MethodBody),
            has_rel(StepConcept, has_method_parameters, MethodParams)
        ),
        Steps
    ),
    Program = program(Concept, InputsStr, OutputsStr, RolesStr, Steps).

% ======================================================================
% COMPILE TO PYTHON — emit Python source string
% ======================================================================

% Quine codegen: emit a Pydantic BaseModel + make() classmethod that,
% when exec'd, registers itself as a SOMA runtime object. Calling the
% registered callable with kwargs produces a new particular (instance)
% representing a fresh realization of the concept.
compile_to_python(Concept, PythonCode) :-
    should_compile(Concept),
    assemble_program(Concept, Program),
    Program = program(Name, InputsStr, OutputsStr, _RolesStr, Steps),
    atom_string(Name, NameStr),
    build_field_decls(InputsStr, InputFields),
    build_field_decls(OutputsStr, OutputFields),
    build_make_body(Steps, InputsStr, OutputsStr, MakeBody),
    build_param_signature(InputsStr, ParamSig),
    build_kwarg_return(InputsStr, OutputsStr, KwargReturn),
    format(atom(PythonCode),
'# Auto-compiled from SOMA observations
# Concept: ~w (all required slots filled -> CODE layer)
# This is a quine: the code exports itself as a runtime object via
# the SOMA runtime registry. Calling ~w(**kwargs) produces a new
# particular (Pydantic instance) of this concept.
from pydantic import BaseModel, Field

class ~w(BaseModel):
    """Runtime object for ~w — each instance is a particular realization."""
~w~w
    @classmethod
    def make(cls, ~w):
~w        return cls(~w)

# Public entry point: flow args in, get a particular out.
~w = ~w.make
',
        [Name, Name, Name, Name, InputFields, OutputFields,
         ParamSig, MakeBody, KwargReturn, Name, Name]),
    % Exec the code into the persistent runtime registry
    py_call('soma_prolog.utils':exec_soma_runtime_code(NameStr, PythonCode), RegStatus),
    get_time(T),
    assert(compiled_program(Concept, PythonCode)),
    assert(compilation_log(Concept, T, compiled(RegStatus))).

% Build Pydantic field declarations from comma-separated field list
build_field_decls(FieldStr, FieldLines) :-
    atom_string(FieldStr, FieldStrS),
    split_string(FieldStrS, ",", " ", FieldList),
    build_field_decl_lines(FieldList, FieldLines).

build_field_decl_lines([], '').
build_field_decl_lines([""|Rest], AllLines) :- !,
    build_field_decl_lines(Rest, AllLines).
build_field_decl_lines([F|Rest], AllLines) :-
    format(atom(Line), '    ~w: str = Field(default="", description="~w slot")~n', [F, F]),
    build_field_decl_lines(Rest, RestLines),
    format(atom(AllLines), '~w~w', [Line, RestLines]).

% Build the make() method body: compute each output field by chaining step bodies
build_make_body([], _InputsStr, _OutputsStr, '        # no steps defined\n').
build_make_body([step(_StepName, MethodBody, _Params)|_Rest], _InputsStr, OutputsStr, Body) :-
    atom_string(OutputsStr, OutStrS),
    split_string(OutStrS, ",", " ", [FirstOut|_]),
    atom_string(FirstOutAtom, FirstOut),
    format(atom(Body),
'        # Derived from step method body
        ~w = f"~w"
', [FirstOutAtom, MethodBody]).

% Build parameter signature like "x, y"
build_param_signature(ParamStr, SigStr) :-
    atom_string(ParamStr, ParamStrS),
    split_string(ParamStrS, ",", " ", Params),
    atomic_list_concat(Params, ', ', SigAtom),
    atom_string(SigAtom, SigStr).

% Build the kwarg-style return argument list like "x=x, y=y, result=result"
% combining input and output field names.
build_kwarg_return(InputsStr, OutputsStr, RetStr) :-
    atom_string(InputsStr, InS),
    atom_string(OutputsStr, OutS),
    split_string(InS, ",", " ", InParts),
    split_string(OutS, ",", " ", OutParts),
    append(InParts, OutParts, AllParts),
    filter_non_empty(AllParts, NonEmpty),
    findall(KV, (member(F, NonEmpty), F \= "", format(atom(KV), '~w=~w', [F, F])), KVList),
    atomic_list_concat(KVList, ', ', RetAtom),
    atom_string(RetAtom, RetStr).

filter_non_empty([], []).
filter_non_empty([""|T], R) :- !, filter_non_empty(T, R).
filter_non_empty([H|T], [H|R]) :- filter_non_empty(T, R).

% Build RenderablePiece classes from steps
build_piece_classes([], '').
build_piece_classes([step(StepName, MethodBody, MethodParams)|Rest], AllClasses) :-
    format(atom(ClassName), '~w', [StepName]),
    build_fields(MethodParams, FieldLines),
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
    atom_string(ParamStr, ParamStrS),
    split_string(ParamStrS, ",", " ", Params),
    build_field_lines(Params, FieldLines).

build_field_lines([], '').
build_field_lines([P|Rest], AllLines) :-
    format(atom(Line), '    ~w: str = Field(description="~w")~n', [P, P]),
    build_field_lines(Rest, RestLines),
    format(atom(AllLines), '~w~w', [Line, RestLines]).

% Build MetaStack assembly in the main function
build_stack_assembly(Steps, Assembly) :-
    build_piece_instantiations(Steps, PieceInsts),
    format(atom(Assembly),
'    stack = MetaStack(pieces=[
~w    ], separator="\\n\\n")
    return stack.render()
', [PieceInsts]).

% Build piece instantiation lines
build_piece_instantiations([], '').
build_piece_instantiations([step(StepName, _MB, MethodParams)|Rest], AllInsts) :-
    format(atom(ClassName), '~w', [StepName]),
    build_kwargs(MethodParams, KwargStr),
    format(atom(Inst), '        ~w(~w),~n', [ClassName, KwargStr]),
    build_piece_instantiations(Rest, RestInsts),
    format(atom(AllInsts), '~w~w', [Inst, RestInsts]).

% Build keyword arguments from params: "x,y" -> "x=x, y=y"
build_kwargs(ParamStr, KwargStr) :-
    atom_string(ParamStr, ParamStrS),
    split_string(ParamStrS, ",", " ", Params),
    build_kwarg_parts(Params, KwargStr).

build_kwarg_parts([], '').
build_kwarg_parts([P], OneKw) :-
    format(atom(OneKw), '~w=~w', [P, P]), !.
build_kwarg_parts([P|Rest], AllKw) :-
    format(atom(Kw), '~w=~w, ', [P, P]),
    build_kwarg_parts(Rest, RestKw),
    format(atom(AllKw), '~w~w', [Kw, RestKw]).

% ======================================================================
% AUTO-COMPILE — compile every ready concept
% ======================================================================

auto_compile_all(Results) :-
    findall(
        compiled(Concept, Status),
        (   should_compile(Concept),
            (   compile_to_python(Concept, _Code)
            ->  Status = success
            ;   Status = failed
            )
        ),
        Results
    ).

% ======================================================================
% RUN COMPILED — execute Python via janus
% ======================================================================

provide_inputs(Concept, InputDict) :-
    assert(runtime_input(Concept, InputDict)).

should_run(Concept) :-
    compiled_program(Concept, _),
    runtime_input(Concept, _).

run_compiled(Concept, KwargsJson, Result) :-
    atom_string(Concept, ConceptStr),
    atom_string(KwargsJson, KwargsStr),
    get_time(T),
    catch(
        py_call('soma_prolog.utils':call_soma_runtime(ConceptStr, KwargsStr), ResultJson),
        Error,
        (   term_to_atom(Error, EA),
            format(atom(ResultJson), '{"error":"~w"}', [EA])
        )
    ),
    Result = ResultJson,
    assert(execution_result(Concept, T, Result)).

% (Legacy exec path removed — runtime calls now go through
% call_soma_runtime in utils.py via the run_compiled/3 clause above.)

% ======================================================================
% INSPECT COMPILED CODE
% ======================================================================

get_compiled_code(Concept, Code) :-
    compiled_program(Concept, Code).

get_compiled_code_str(Concept, Str) :-
    (   compiled_program(Concept, Code)
    ->  format(atom(Str), 'COMPILED: ~w~n~n~w', [Concept, Code])
    ;   format(atom(Str), 'NOT COMPILED: ~w', [Concept])
    ).

% ======================================================================
% JANUS WRAPPERS
% ======================================================================

compile_all_str(Str) :-
    auto_compile_all(Results),
    length(Results, N),
    with_output_to(atom(Str),
        (   format('Compiled ~w concepts:~n', [N]),
            forall(member(compiled(C, S), Results),
                format('  ~w: ~w~n', [C, S])
            )
        )).
