"""Pure expansion and RN-06 preparation of detached, validated snapshots."""
from dataclasses import dataclass
from decimal import Decimal

from .problem import MaterialGroup, OptimizationConfig, OptimizationProblem, PieceUnit, positive_int


@dataclass(frozen=True, kw_only=True)
class PieceSnapshot:
    """One persisted piece and its quantity; unit carries its immutable metadata."""
    unit: PieceUnit
    quantity: int

    def __post_init__(self):
        positive_int(self.quantity, "quantity")
        if self.unit.unit_index != 1:
            raise ValueError("A piece snapshot starts at unit_index=1.")


def bbox_dimensions(geometry) -> tuple[Decimal, Decimal]:
    """Decimal arithmetic over canonical JSON numbers, without binary conversion."""
    if geometry["type"] == "RECTANGULO":
        return tuple(Decimal(str(geometry[k])) for k in ("width_mm", "height_mm"))
    if geometry["type"] == "CIRCUNFERENCIA":
        return (2 * Decimal(str(geometry["radius_mm"])),) * 2
    vertices = geometry["vertices_mm"]
    return tuple(max(Decimal(str(p[i])) for p in vertices)
                 - min(Decimal(str(p[i])) for p in vertices) for i in (0, 1))


def prepare_group_units(units) -> tuple[PieceUnit, ...]:
    return tuple(sorted(units, key=lambda u: (
        -u.area_mm2, -max(bbox_dimensions(u.geometry)), u.order_id, u.piece_id, u.unit_index,
    )))


def prepare_problem(order_ids, pieces, config: OptimizationConfig) -> OptimizationProblem:
    """Expand 1..N before grouping. Never read a database or mutate snapshots."""
    from dataclasses import replace

    groups = {}
    seen = set()
    for snapshot in pieces:
        piece = snapshot.unit
        if piece.piece_id in seen:
            raise ValueError("Duplicate persisted piece ID.")
        seen.add(piece.piece_id)
        units = groups.setdefault(piece.material_key, [])
        units.extend(replace(piece, unit_index=i) for i in range(1, snapshot.quantity + 1))
    # OptimizationProblem enforces nonempty, unique selection and exact coverage.
    return OptimizationProblem(
        order_ids=tuple(sorted(order_ids)), config=config,
        groups=tuple(MaterialGroup(glass_type_id=key[0], thickness_mm=key[1],
                                   units=prepare_group_units(groups[key])) for key in sorted(groups)),
    )
