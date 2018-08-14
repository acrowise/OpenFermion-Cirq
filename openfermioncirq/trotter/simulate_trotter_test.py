#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from typing import Optional, Tuple

import numpy
import pytest
import scipy.sparse.linalg

import cirq
import openfermion
from openfermion.utils._testing_utils import (
        random_diagonal_coulomb_hamiltonian,
        random_interaction_operator)

from openfermioncirq import simulate_trotter
from openfermioncirq.trotter import (
        SPLIT_OPERATOR,
        LINEAR_SWAP_NETWORK,
        LOW_RANK,
        LowRankTrotterAlgorithm,
        TrotterAlgorithm)
from openfermioncirq.trotter.trotter_algorithm import Hamiltonian


def fidelity(state1, state2):
    return abs(numpy.dot(state1, numpy.conjugate(state2)))**2


def load_molecular_hamiltonian(
        geometry,
        basis,
        multiplicity,
        description,
        n_active_electrons,
        n_active_orbitals):

    molecule = openfermion.MolecularData(
            geometry, basis, multiplicity, description=description)
    molecule.load()

    n_core_orbitals = (molecule.n_electrons - n_active_electrons) // 2
    occupied_indices = list(range(n_core_orbitals))
    active_indices = list(range(n_core_orbitals,
                                n_core_orbitals + n_active_orbitals))

    return molecule.get_molecular_hamiltonian(
            occupied_indices=occupied_indices,
            active_indices=active_indices)


def produce_simulation_test_parameters(
        hamiltonian: Hamiltonian,
        time: float,
        seed: Optional[int]=None
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """Produce objects for testing Hamiltonian simulation.

    Produces a random initial state and evolves it under the given Hamiltonian
    for the specified amount of time. Returns the initial state and final
    state.

    Args:
        hamiltonian: The Hamiltonian to evolve under.
        time: The time to evolve for
        seed: An RNG seed.
    """

    n_qubits = openfermion.count_qubits(hamiltonian)

    # Construct a random initial state
    initial_state = openfermion.haar_random_vector(2**n_qubits, seed)

    # Simulate exact evolution
    hamiltonian_sparse = openfermion.get_sparse_operator(hamiltonian)
    exact_state = scipy.sparse.linalg.expm_multiply(
            -1j * time * hamiltonian_sparse, initial_state)

    # Make sure the time is not too small
    assert fidelity(exact_state, initial_state) < .95

    return initial_state, exact_state


# Produce test objects

bigger_time = 1.0
big_time = 0.1
small_time = 0.05

# 5-qubit random DiagonalCoulombHamiltonian
diag_coul_hamiltonian = random_diagonal_coulomb_hamiltonian(
        5, real=False, seed=65233)
diag_coul_initial_state, diag_coul_exact_state = (
        produce_simulation_test_parameters(
            diag_coul_hamiltonian, big_time, seed=49075)
)

# 4-qubit H2 2-2 with bond length 0.7414
bond_length = 0.7414
geometry = [('H', (0., 0., 0.)), ('H', (0., 0., bond_length))]
h2_hamiltonian = load_molecular_hamiltonian(
        geometry, 'sto-3g', 1, format(bond_length), 2, 2)
h2_initial_state, h2_exact_state = produce_simulation_test_parameters(
        h2_hamiltonian, bigger_time, seed=44303)

# 4-qubit LiH 2-2 with bond length 1.45
bond_length = 1.45
geometry = [('Li', (0., 0., 0.)), ('H', (0., 0., bond_length))]
lih_hamiltonian = load_molecular_hamiltonian(
        geometry, 'sto-3g', 1, format(bond_length), 2, 2)
lih_initial_state, lih_exact_state = produce_simulation_test_parameters(
        lih_hamiltonian, bigger_time, seed=54458)

# 3-qubit random InteractionOperator
interaction_op3 = random_interaction_operator(
        3, real=True, seed=53404)
interaction_op_initial_state3, interaction_op_exact_state3 = (
        produce_simulation_test_parameters(
            interaction_op3, big_time, seed=48565)
)

# 4-qubit random InteractionOperator
interaction_op4 = random_interaction_operator(
        4, real=True, seed=60822)
interaction_op_initial_state4, interaction_op_exact_state4 = (
        produce_simulation_test_parameters(
            interaction_op4, small_time, seed=19372)
)


@pytest.mark.parametrize(
        'hamiltonian, time, initial_state, exact_state, order, n_steps, '
        'algorithm, result_fidelity', [
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 5, None, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 12, None, .999),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 1, 1, LINEAR_SWAP_NETWORK, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 2, 1, LINEAR_SWAP_NETWORK, .99999),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 3, SPLIT_OPERATOR, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 6, SPLIT_OPERATOR, .999),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 1, 1, SPLIT_OPERATOR, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 2, 1, SPLIT_OPERATOR, .99999),
            (h2_hamiltonian, bigger_time, h2_initial_state,
                h2_exact_state, 0, 1, LOW_RANK, .99),
            (h2_hamiltonian, bigger_time, h2_initial_state,
                h2_exact_state, 0, 10, LOW_RANK, .9999),
            (lih_hamiltonian, bigger_time, lih_initial_state, lih_exact_state,
                0, 1, LowRankTrotterAlgorithm(final_rank=15), .999),
            (lih_hamiltonian, bigger_time, lih_initial_state, lih_exact_state,
                0, 10, LowRankTrotterAlgorithm(final_rank=15), .9999),
            (interaction_op3, big_time, interaction_op_initial_state3,
                interaction_op_exact_state3, 0, 1, None, .998),
            (interaction_op3, big_time, interaction_op_initial_state3,
                interaction_op_exact_state3, 0, 2, LOW_RANK, .999),
            (interaction_op4, small_time, interaction_op_initial_state4,
                interaction_op_exact_state4, 0, 1, LOW_RANK, .991),
            (interaction_op4, small_time, interaction_op_initial_state4,
                interaction_op_exact_state4, 0, 2, LOW_RANK, .998),
])
def test_simulate_trotter_simulate(
        hamiltonian, time, initial_state, exact_state, order, n_steps,
        algorithm, result_fidelity):

    n_qubits = openfermion.count_qubits(hamiltonian)
    qubits = cirq.LineQubit.range(n_qubits)

    start_state = initial_state

    circuit = cirq.Circuit.from_ops(simulate_trotter(
        qubits, hamiltonian, time, n_steps, order, algorithm))

    final_state = circuit.apply_unitary_effect_to_state(start_state)
    correct_state = exact_state
    assert fidelity(final_state, correct_state) > result_fidelity
    # Make sure the time wasn't too small
    assert fidelity(final_state, start_state) < 0.95 * result_fidelity


@pytest.mark.parametrize(
        'hamiltonian, time, initial_state, exact_state, order, n_steps, '
        'algorithm, result_fidelity', [
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 5, None, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 12, None, .999),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 1, 1, LINEAR_SWAP_NETWORK, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 2, 1, LINEAR_SWAP_NETWORK, .99999),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 3, SPLIT_OPERATOR, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 0, 6, SPLIT_OPERATOR, .999),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 1, 1, SPLIT_OPERATOR, .99),
            (diag_coul_hamiltonian, big_time, diag_coul_initial_state,
                diag_coul_exact_state, 2, 1, SPLIT_OPERATOR, .99999),
            (h2_hamiltonian, bigger_time, h2_initial_state,
                h2_exact_state, 0, 1, LOW_RANK, .99),
            (h2_hamiltonian, bigger_time, h2_initial_state,
                h2_exact_state, 0, 10, LOW_RANK, .9999),
            (lih_hamiltonian, bigger_time, lih_initial_state, lih_exact_state,
                0, 1, LowRankTrotterAlgorithm(final_rank=15), .999),
            (lih_hamiltonian, bigger_time, lih_initial_state, lih_exact_state,
                0, 10, LowRankTrotterAlgorithm(final_rank=15), .9999),
            (interaction_op3, big_time, interaction_op_initial_state3,
                interaction_op_exact_state3, 0, 1, LOW_RANK, .9991),
            (interaction_op3, big_time, interaction_op_initial_state3,
                interaction_op_exact_state3, 0, 2, LOW_RANK, .9998),
            (interaction_op4, small_time, interaction_op_initial_state4,
                interaction_op_exact_state4, 0, 1, LOW_RANK, .995),
            (interaction_op4, small_time, interaction_op_initial_state4,
                interaction_op_exact_state4, 0, 2, LOW_RANK, .998),
])
def test_simulate_trotter_simulate_controlled(
        hamiltonian, time, initial_state, exact_state, order, n_steps,
        algorithm, result_fidelity):

    n_qubits = openfermion.count_qubits(hamiltonian)
    qubits = cirq.LineQubit.range(n_qubits)

    control = cirq.LineQubit(-1)
    zero = [1, 0]
    one = [0, 1]
    start_state = (numpy.kron(zero, initial_state)
                   + numpy.kron(one, initial_state)) / numpy.sqrt(2)

    circuit = cirq.Circuit.from_ops(simulate_trotter(
        qubits, hamiltonian, time, n_steps, order, algorithm, control))

    final_state = circuit.apply_unitary_effect_to_state(start_state)
    correct_state = (numpy.kron(zero, initial_state)
                     + numpy.kron(one, exact_state)) / numpy.sqrt(2)
    assert fidelity(final_state, correct_state) > result_fidelity
    # Make sure the time wasn't too small
    assert fidelity(final_state, start_state) < 0.95 * result_fidelity


def test_simulate_trotter_omit_final_swaps():
    n_qubits = 5
    qubits = cirq.LineQubit.range(n_qubits)
    hamiltonian = openfermion.DiagonalCoulombHamiltonian(
            one_body=numpy.ones((n_qubits, n_qubits)),
            two_body=numpy.ones((n_qubits, n_qubits)))
    time = 1.0

    circuit_with_swaps = cirq.Circuit.from_ops(
            simulate_trotter(
                qubits, hamiltonian, time, order=0,
                algorithm=LINEAR_SWAP_NETWORK))
    circuit_without_swaps = cirq.Circuit.from_ops(
            simulate_trotter(
                qubits, hamiltonian, time, order=0,
                algorithm=LINEAR_SWAP_NETWORK,
                omit_final_swaps=True))

    assert (circuit_with_swaps.to_text_diagram(transpose=True).strip() ==
            (circuit_without_swaps.to_text_diagram(transpose=True).strip() + """
│        ×ᶠ─────────×ᶠ         ×ᶠ─────────×ᶠ
│        │          │          │          │
×ᶠ───────×ᶠ         ×ᶠ─────────×ᶠ         │
│        │          │          │          │
│        ×ᶠ─────────×ᶠ         ×ᶠ─────────×ᶠ
│        │          │          │          │
×ᶠ───────×ᶠ         ×ᶠ─────────×ᶠ         │
│        │          │          │          │
│        ×ᶠ─────────×ᶠ         ×ᶠ─────────×ᶠ
│        │          │          │          │
""").strip())

    circuit_with_swaps = cirq.Circuit.from_ops(
            simulate_trotter(
                qubits,
                hamiltonian,
                time,
                order=1,
                n_steps=3,
                algorithm=SPLIT_OPERATOR),
            strategy=cirq.InsertStrategy.NEW)
    circuit_without_swaps = cirq.Circuit.from_ops(
            simulate_trotter(
                qubits,
                hamiltonian,
                time,
                order=1,
                n_steps=3,
                algorithm=SPLIT_OPERATOR,
                omit_final_swaps=True),
            strategy=cirq.InsertStrategy.NEW)

    assert (circuit_with_swaps.to_text_diagram(transpose=True).strip() ==
            (circuit_without_swaps.to_text_diagram(transpose=True).strip() + """
│         │           │           ×────────────×
│         │           │           │            │
│         ×───────────×           │            │
│         │           │           │            │
│         │           ×───────────×            │
│         │           │           │            │
×─────────×           │           │            │
│         │           │           │            │
│         │           │           ×────────────×
│         │           │           │            │
│         ×───────────×           │            │
│         │           │           │            │
│         │           ×───────────×            │
│         │           │           │            │
×─────────×           │           │            │
│         │           │           │            │
│         │           │           ×────────────×
│         │           │           │            │
│         ×───────────×           │            │
│         │           │           │            │
""").strip())

    hamiltonian = random_interaction_operator(n_qubits, seed=0)
    circuit_with_swaps = cirq.Circuit.from_ops(
            simulate_trotter(
                qubits, hamiltonian, time, order=0,
                algorithm=LOW_RANK))
    circuit_without_swaps = cirq.Circuit.from_ops(
            simulate_trotter(
                qubits, hamiltonian, time, order=0,
                algorithm=LOW_RANK,
                omit_final_swaps=True))

    assert len(circuit_without_swaps) < len(circuit_with_swaps)


def test_simulate_trotter_bad_order_raises_error():
    qubits = cirq.LineQubit.range(2)
    hamiltonian = random_diagonal_coulomb_hamiltonian(2, seed=0)
    time = 1.0
    with pytest.raises(ValueError):
        _ = next(simulate_trotter(qubits, hamiltonian, time, order=-1))


def test_simulate_trotter_bad_hamiltonian_type_raises_error():
    qubits = cirq.LineQubit.range(2)
    hamiltonian = openfermion.FermionOperator()
    time = 1.0
    with pytest.raises(TypeError):
        _ = next(simulate_trotter(qubits, hamiltonian, time,
                                  algorithm=None))
    with pytest.raises(TypeError):
        _ = next(simulate_trotter(qubits, hamiltonian, time,
                                  algorithm=LINEAR_SWAP_NETWORK))


def test_simulate_trotter_unsupported_trotter_step_raises_error():
    qubits = cirq.LineQubit.range(2)
    control = cirq.LineQubit(-1)
    hamiltonian = random_diagonal_coulomb_hamiltonian(2, seed=0)
    time = 1.0
    class EmptyTrotterAlgorithm(TrotterAlgorithm):
        supported_types = {openfermion.DiagonalCoulombHamiltonian}
    algorithm = EmptyTrotterAlgorithm()
    with pytest.raises(ValueError):
        _ = next(simulate_trotter(qubits, hamiltonian, time, order=0,
                                  algorithm=algorithm))
    with pytest.raises(ValueError):
        _ = next(simulate_trotter(qubits, hamiltonian, time, order=1,
                                  algorithm=algorithm))
    with pytest.raises(ValueError):
        _ = next(simulate_trotter(qubits, hamiltonian, time, order=0,
                                  algorithm=algorithm, control_qubit=control))
    with pytest.raises(ValueError):
        _ = next(simulate_trotter(qubits, hamiltonian, time, order=1,
                                  algorithm=algorithm, control_qubit=control))
