const { useState, useEffect } = React;

const API_BASE = "http://localhost:8000/api";
const MEDIA_BASE = "http://localhost:8000";

const App = () => {
    const [stats, setStats] = useState(null);
    const [recursos, setRecursos] = useState([]);
    const [totalItems, setTotalItems] = useState(0);
    const [loading, setLoading] = useState(true);

    // Filters & Pagination
    const [search, setSearch] = useState("");
    const [searchTerm, setSearchTerm] = useState("");
    const [page, setPage] = useState(0);
    const [viewMode, setViewMode] = useState("grid"); // grid or list
    const limit = 24;

    const [filtroFav, setFiltroFav] = useState(false);
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const [sortOrder, setSortOrder] = useState("desc");

    // Modal State
    const [editingItem, setEditingItem] = useState(null);
    const [previewItem, setPreviewItem] = useState(null);
    const [showTaxonomy, setShowTaxonomy] = useState(false);

    useEffect(() => {
        fetchStats();
    }, []);

    useEffect(() => {
        const timer = setTimeout(() => {
            setSearchTerm(search);
            setPage(0); // Reset page on new search
        }, 500);
        return () => clearTimeout(timer);
    }, [search]);

    useEffect(() => {
        fetchRecursos();
    }, [searchTerm, page, filtroFav, dateFrom, dateTo, sortOrder]);

    const fetchStats = async () => {
        try {
            const res = await fetch(`${API_BASE}/stats`);
            setStats(await res.json());
        } catch (err) { console.error("Error fetching stats:", err); }
    };

    const fetchRecursos = async () => {
        setLoading(true);
        try {
            let url = `${API_BASE}/recursos?skip=${page * limit}&limit=${limit}&order=${sortOrder}`;
            if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`;
            if (filtroFav) url += `&favorito=true`;
            if (dateFrom) url += `&date_from=${dateFrom}`;
            if (dateTo) url += `&date_to=${dateTo}`;

            const res = await fetch(url);
            const data = await res.json();
            setRecursos(data.items);
            setTotalItems(data.total);
        } catch (err) { console.error("Error fetching", err); }
        finally { setLoading(false); }
    };

    const toggleFav = async (id) => {
        try {
            const res = await fetch(`${API_BASE}/recursos/${id}/favorito`, { method: 'PUT' });
            if (res.ok) {
                const { favorito } = await res.json();
                setRecursos(recursos.map(r => r.id === id ? { ...r, favorito } : r));
            }
        } catch (err) { console.error(err); }
    };

    const deleteRecurso = async (id) => {
        if (!confirm("¿Seguro que quieres eliminar este recurso de la base de datos?")) return;
        try {
            const res = await fetch(`${API_BASE}/recursos/${id}`, { method: 'DELETE' });
            if (res.ok) { fetchRecursos(); fetchStats(); }
        } catch (err) { console.error(err); }
    };

    const updateRecurso = async (e) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_BASE}/recursos/${editingItem.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contenido: editingItem.contenido,
                    etiqueta: editingItem.etiqueta
                })
            });
            if (res.ok) {
                setEditingItem(null);
                fetchRecursos();
            }
        } catch (err) { console.error(err); }
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('es-ES', {
            day: '2-digit', month: 'short', year: 'numeric'
        });
    };

    const getMediaPath = (contenido) => {
        const match = contenido.match(/Archivo:\s*(.+)/);
        if (match) return match[1].trim().replace(/\\/g, '/');
        return contenido;
    };

    const renderMedia = (recurso, isDetailed = false) => {
        const { tipo, contenido } = recurso;
        if (tipo === 'foto') {
            const path = getMediaPath(contenido);
            const filename = path.split('/').pop();
            const imgUrl = `${MEDIA_BASE}/fotos/${filename}`;
            return (
                <div style={{ position: 'relative' }}>
                    <img
                        src={imgUrl}
                        className={isDetailed ? "preview-image" : "resource-image"}
                        alt="Previsualización"
                    />
                    {isDetailed && (
                        <a href={imgUrl} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ display: 'inline-block', marginBottom: '1rem' }}>
                            ↗️ Abrir Imagen Original
                        </a>
                    )}
                </div>
            );
        }
        return null;
    };

    const renderContent = (recurso, isDetailed = false) => {
        const { tipo, contenido } = recurso;

        if (tipo === 'link') {
            return (
                <div>
                    <a href={contenido} target="_blank" className="card-link" rel="noreferrer">🔗 {contenido}</a>
                    {isDetailed && (
                        <div className="link-preview-container">
                            <iframe src={contenido} title="Link Preview" loading="lazy"></iframe>
                        </div>
                    )}
                </div>
            );
        }

        if (tipo === 'foto' || tipo === 'pdf') {
            const parts = contenido.split(/Archivo:/);
            const text = parts[0].trim();
            const path = parts.length > 1 ? parts[1].trim() : '';
            const filename = path.split('\\').pop().split('/').pop();

            return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {text && <div>💬 {text}</div>}
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>📁 {filename || 'Archivo guardado'}</div>
                    {isDetailed && tipo === 'pdf' && path && (
                        <a href={`${MEDIA_BASE}/documentos/${filename}`} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ alignSelf: 'flex-start', marginTop: '1rem' }}>
                            📄 Abrir PDF Original
                        </a>
                    )}
                </div>
            );
        }

        return <div style={{ whiteSpace: 'pre-wrap' }}>{contenido}</div>;
    };

    const getTypeIcon = (tipo) => {
        switch (tipo) {
            case 'foto': return '🖼️';
            case 'link': return '🔗';
            case 'pdf': return '📄';
            default: return '📝';
        }
    }

    return (
        <div className="app-container">
            <div className="bg-blobs"><div className="blob blob-1"></div><div className="blob blob-2"></div></div>

            <aside className="sidebar">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ background: 'var(--accent)', padding: '0.5rem', borderRadius: '12px', display: 'flex', fontSize: '1.5rem' }}>🧠</div>
                    <h2>Cerebro AI</h2>
                </div>

                <div className="filter-section">
                    <h3>Vistas Rápidas</h3>
                    <button className={`filter-btn ${!filtroFav ? 'active' : ''}`} onClick={() => { setFiltroFav(false); setPage(0); }}>📚 Todos los Recursos</button>
                    <button className={`filter-btn ${filtroFav ? 'active' : ''}`} onClick={() => { setFiltroFav(true); setPage(0); }}>⭐ Favoritos</button>
                </div>

                <div className="filter-section">
                    <h3>Rango de Fechas</h3>
                    <div className="date-inputs">
                        <label>Desde:</label>
                        <input type="date" className="filter-btn" style={{ margin: 0 }} value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(0); }} />

                        <label style={{ marginTop: '0.5rem' }}>Hasta:</label>
                        <input type="date" className="filter-btn" style={{ margin: 0 }} value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(0); }} />
                    </div>
                </div>

                <div className="filter-section">
                    <h3>Orden por Fecha</h3>
                    <select className="filter-btn" style={{ width: '100%' }} value={sortOrder} onChange={e => setSortOrder(e.target.value)}>
                        <option value="desc">🔽 Más recientes primero</option>
                        <option value="asc">🔼 Más antiguos primero</option>
                    </select>
                </div>

                <div style={{ marginTop: 'auto', padding: '1rem 0' }}>
                    <button
                        className="btn btn-secondary"
                        style={{ width: '100%', fontSize: '0.8rem', opacity: 0.7 }}
                        onClick={() => setShowTaxonomy(true)}
                    >
                        🏷️ Ayuda Etiquetas
                    </button>
                </div>
            </aside>

            <main className="main-content">
                <header className="header">
                    <div className="search-bar">
                        <span style={{ marginRight: '0.5rem' }}>🔍</span>
                        <input type="text" placeholder="Buscar texto o etiquetas..." value={search} onChange={e => setSearch(e.target.value)} />
                    </div>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Ver como:</span>
                        <div className="glass-panel" style={{ padding: '5px', borderRadius: '10px', display: 'flex' }}>
                            <button className={`btn-icon ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')} title="Vista de Cuadrícula">🔲 Grid</button>
                            <button className={`btn-icon ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')} title="Vista de Lista">📜 Lista</button>
                        </div>
                    </div>
                </header>

                <div className={`content-scroll resource-container ${viewMode === 'list' ? 'list-view' : ''}`}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h2>
                            {search ? `Resultados para "${search}"` : filtroFav ? 'Tus Favoritos' : 'Todos los Recursos'}
                            <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 'normal', marginLeft: '1rem' }}>({totalItems} encontrados)</span>
                        </h2>
                    </div>

                    {loading ? (
                        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
                            <div>Cargando...</div>
                        </div>
                    ) : recursos.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '4rem', background: 'var(--card-bg)', borderRadius: '16px', border: '1px dashed var(--card-border)' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
                            <h3>No se encontraron resultados</h3>
                        </div>
                    ) : (
                        <div className="resource-grid">
                            {recursos.map(r => (
                                <div key={r.id} className="glass-panel resource-card">
                                    {viewMode === 'grid' && renderMedia(r, false)}
                                    <div className="card-header">
                                        <div className="card-type" style={{ color: 'var(--text-muted)' }}>
                                            {getTypeIcon(r.tipo)} {r.tipo.toUpperCase()}
                                        </div>
                                        <div className="card-date">{formatDate(r.fecha)}</div>
                                    </div>

                                    <div className="card-content" onClick={() => setPreviewItem(r)} style={{ cursor: 'pointer' }} title="Clic para ampliar">
                                        {renderContent(r, false)}
                                    </div>

                                    <div className="card-tags">
                                        {r.etiqueta && r.etiqueta !== "SinEtiqueta" ? (
                                            r.etiqueta.split(',').map((t, i) => (
                                                <span key={i} className="tag" onClick={() => setSearch(t.trim())}>#{t.trim()}</span>
                                            ))
                                        ) : (
                                            <span className="tag" style={{ opacity: 0.5, borderColor: 'transparent', background: 'rgba(255,255,255,0.05)' }}>🏷️ Sin etiquetas</span>
                                        )}
                                    </div>

                                    <div className="card-actions">
                                        <button className={`btn-icon ${r.favorito ? 'active' : ''}`} onClick={() => toggleFav(r.id)} title="Favorito">
                                            {r.favorito ? '⭐' : '☆'}
                                        </button>
                                        <button className="btn-icon" onClick={() => setEditingItem(r)} title="Editar">📝 Editar</button>
                                        <button className="btn-icon danger" onClick={() => deleteRecurso(r.id)} title="Eliminar">🗑️ Borrar</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Pagination */}
                    {totalItems > limit && (
                        <div className="pagination">
                            <button className="btn-page" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
                                ◀ Anterior
                            </button>
                            <span style={{ color: '#fff', fontSize: '1rem', fontWeight: 600 }}>
                                Página {page + 1} de {Math.ceil(totalItems / limit)}
                            </span>
                            <button className="btn-page" disabled={(page + 1) * limit >= totalItems} onClick={() => setPage(p => p + 1)}>
                                Siguiente ▶
                            </button>
                        </div>
                    )}
                </div>
            </main>

            {/* Edit Modal */}
            {editingItem && (
                <div className="modal-overlay">
                    <div className="glass-panel modal-content">
                        <h2>✏️ Editar Recurso</h2>
                        <form onSubmit={updateRecurso}>
                            <div className="form-group">
                                <label>Contenido (Texto / Link / Archivo)</label>
                                <textarea rows="6" value={editingItem.contenido} onChange={e => setEditingItem({ ...editingItem, contenido: e.target.value })} />
                            </div>
                            <div className="form-group">
                                <label>Etiquetas (separadas por coma)</label>
                                <input type="text" value={editingItem.etiqueta} onChange={e => setEditingItem({ ...editingItem, etiqueta: e.target.value })} placeholder="Ej: ProyectoX, Idea, Referencia" />
                            </div>
                            <div className="btn-group">
                                <button type="button" className="btn btn-secondary" onClick={() => setEditingItem(null)}>Cancelar</button>
                                <button type="submit" className="btn btn-primary">💾 Guardar Cambios</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Preview Modal */}
            {previewItem && (
                <div className="modal-overlay" onClick={() => setPreviewItem(null)} style={{ padding: '2rem' }}>
                    <div className="glass-panel modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '900px', width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
                        <div className="card-header" style={{ marginBottom: '1rem', position: 'sticky', top: 0, background: 'var(--card-bg)', zIndex: 10, padding: '1rem 0', margin: '-1rem 0 1rem 0' }}>
                            <h2 style={{ margin: 0 }}>📖 Vista Detallada</h2>
                            <button className="btn-icon" onClick={() => setPreviewItem(null)}>❌</button>
                        </div>
                        <div className="full-text-preview" style={{ maxHeight: 'none', paddingRight: '1rem' }}>
                            <div style={{ marginBottom: '1rem' }}>{renderMedia(previewItem, true)}</div>
                            <div style={{ fontSize: '1.1rem', lineHeight: '1.6' }}>
                                {renderContent(previewItem, true)}
                            </div>
                        </div>
                        <div className="btn-group">
                            <button className="btn btn-secondary" onClick={() => setPreviewItem(null)}>Cerrar</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Taxonomy Modal */}
            {showTaxonomy && (
                <div className="modal-overlay" onClick={() => setShowTaxonomy(false)}>
                    <div className="glass-panel modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', width: '90%' }}>
                        <div className="card-header" style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                            <h2 style={{ margin: 0 }}>🏷️ Guía de Taxonomía</h2>
                            <button className="btn-icon" onClick={() => setShowTaxonomy(false)}>❌</button>
                        </div>

                        <div className="taxonomy-grid">
                            <div className="taxonomy-col">
                                <h4>Nivel 1: Macrocategorías</h4>
                                <ul>
                                    <li><strong>#LaAgencia:</strong> Clientes, operaciones, ventas.</li>
                                    <li><strong>#MiMarcaPersonal:</strong> Contenido, branding, redes.</li>
                                    <li><strong>#Varios:</strong> Todo lo demás (finanzas, vida, ideas sueltas).</li>
                                </ul>
                            </div>

                            <div className="taxonomy-col">
                                <h4>Nivel 2: Casos de Uso Frecuentes</h4>
                                <ul>
                                    <li><strong>#Ideas:</strong> Inspiración pura.</li>
                                    <li><strong>#Herramientas:</strong> Software, apps, utilidades.</li>
                                    <li><strong>#Referencias:</strong> Cosas para mirar después.</li>
                                    <li><strong>#Proyectos:</strong> Trabajos activos.</li>
                                    <li><strong>#Novedades:</strong> Noticias, tendencias.</li>
                                </ul>
                            </div>
                        </div>

                        <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '8px', fontSize: '0.9rem' }}>
                            💡 <strong>Tip:</strong> Intenta usar siempre una etiqueta de <strong>Nivel 1</strong> y otra de <strong>Nivel 2</strong> juntas para mantener todo organizado (ej: <code>#LaAgencia, #Ideas</code>).
                        </div>

                        <div className="btn-group">
                            <button className="btn btn-primary" onClick={() => setShowTaxonomy(false)}>Entendido</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
