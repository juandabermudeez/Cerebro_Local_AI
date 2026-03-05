const { useState, useEffect } = React;

const API_BASE = "http://localhost:8000/api";
const MEDIA_BASE = "http://localhost:8000";

const App = () => {
    const [recursos, setRecursos] = useState([]);
    const [totalItems, setTotalItems] = useState(0);
    const [loading, setLoading] = useState(true);

    const [search, setSearch] = useState("");
    const [searchTerm, setSearchTerm] = useState("");
    const [page, setPage] = useState(0);
    const [viewMode, setViewMode] = useState("grid");
    const limit = 24;

    const [filtroFav, setFiltroFav] = useState(false);
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const [sortOrder, setSortOrder] = useState("desc");

    // Modal State
    const [editingItem, setEditingItem] = useState(null);
    const [previewItem, setPreviewItem] = useState(null);
    const [showTaxonomy, setShowTaxonomy] = useState(false);

    // AI States
    const [aiLoading, setAiLoading] = useState(false);
    const [aiResult, setAiResult] = useState("");
    const [aiStatus, setAiStatus] = useState(null);
    const [searchMode, setSearchMode] = useState("normal"); // normal or semantic
    const [showDigest, setShowDigest] = useState(false);
    const [digestContent, setDigestContent] = useState("");
    const [showChat, setShowChat] = useState(false);
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");
    const [bulkTagging, setBulkTagging] = useState(false);

    useEffect(() => {
        checkAiStatus();
    }, []);

    useEffect(() => {
        const timer = setTimeout(() => {
            setSearchTerm(search);
            setPage(0);
        }, 500);
        return () => clearTimeout(timer);
    }, [search]);

    useEffect(() => {
        fetchRecursos();
    }, [searchTerm, page, filtroFav, dateFrom, dateTo, sortOrder]);

    const checkAiStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/ai/status`);
            setAiStatus(await res.json());
        } catch (e) { setAiStatus({ active_engine: "none" }); }
    };

    const fetchRecursos = async () => {
        setLoading(true);
        try {
            // If semantic search mode and there's a term, use AI search
            if (searchMode === "semantic" && searchTerm) {
                const res = await fetch(`${API_BASE}/ai/search`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: searchTerm })
                });
                const data = await res.json();
                setRecursos(data.items);
                setTotalItems(data.total);
            } else {
                let url = `${API_BASE}/recursos?skip=${page * limit}&limit=${limit}&order=${sortOrder}`;
                if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`;
                if (filtroFav) url += `&favorito=true`;
                if (dateFrom) url += `&date_from=${dateFrom}`;
                if (dateTo) url += `&date_to=${dateTo}`;
                const res = await fetch(url);
                const data = await res.json();
                setRecursos(data.items);
                setTotalItems(data.total);
            }
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
        if (!confirm("¿Seguro que quieres eliminar este recurso?")) return;
        try {
            const res = await fetch(`${API_BASE}/recursos/${id}`, { method: 'DELETE' });
            if (res.ok) fetchRecursos();
        } catch (err) { console.error(err); }
    };

    const updateRecurso = async (e) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_BASE}/recursos/${editingItem.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contenido: editingItem.contenido, etiqueta: editingItem.etiqueta })
            });
            if (res.ok) { setEditingItem(null); fetchRecursos(); }
        } catch (err) { console.error(err); }
    };

    // ─── AI Actions ─────────────────────────────
    const handleSummarize = async (text) => {
        setAiLoading(true); setAiResult("");
        try {
            const res = await fetch(`${API_BASE}/ai/summarize`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();
            setAiResult(data.summary);
        } catch { setAiResult("Error al conectar con la IA."); }
        finally { setAiLoading(false); }
    };

    const handleSuggestTags = async (text) => {
        setAiLoading(true);
        try {
            const res = await fetch(`${API_BASE}/ai/suggest_tags`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();
            if (data.tags) {
                const current = editingItem.etiqueta && editingItem.etiqueta !== "SinEtiqueta" ? editingItem.etiqueta : "";
                const newTags = data.tags.join(", ");
                setEditingItem({ ...editingItem, etiqueta: current ? `${current}, ${newTags}` : newTags });
            }
        } catch { alert("Error consultando sugerencias."); }
        finally { setAiLoading(false); }
    };

    const handleDigest = async () => {
        setShowDigest(true); setDigestContent(""); setAiLoading(true);
        try {
            const res = await fetch(`${API_BASE}/ai/digest`);
            const data = await res.json();
            setDigestContent(data.digest);
        } catch { setDigestContent("Error generando el resumen semanal."); }
        finally { setAiLoading(false); }
    };

    const handleChatSend = async () => {
        if (!chatInput.trim()) return;
        const question = chatInput;
        setChatMessages(prev => [...prev, { role: "user", text: question }]);
        setChatInput(""); setAiLoading(true);
        try {
            const res = await fetch(`${API_BASE}/ai/chat`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: question })
            });
            const data = await res.json();
            setChatMessages(prev => [...prev, { role: "ai", text: data.answer }]);
        } catch { setChatMessages(prev => [...prev, { role: "ai", text: "Error conectando con la IA." }]); }
        finally { setAiLoading(false); }
    };

    const handleBulkTag = async () => {
        if (!confirm("¿Etiquetar automáticamente TODOS los recursos sin etiqueta? Esto puede tomar unos minutos.")) return;
        setBulkTagging(true);
        try {
            const res = await fetch(`${API_BASE}/ai/bulk_tag`, { method: 'POST' });
            const data = await res.json();
            alert(`✅ Listo:\n• Total sin etiqueta: ${data.total}\n• Etiquetados: ${data.tagged}\n• Errores: ${data.errors}`);
            fetchRecursos();
        } catch { alert("Error en el etiquetado masivo."); }
        finally { setBulkTagging(false); }
    };

    // ─── Helpers ─────────────────────────────────
    const formatDate = (ds) => new Date(ds).toLocaleString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });

    const getMediaPath = (c) => { const m = c.match(/Archivo:\s*(.+)/); return m ? m[1].trim().replace(/\\/g, '/') : c; };

    const getTypeIcon = (t) => ({ foto: '🖼️', link: '🔗', pdf: '📄' }[t] || '📝');

    const renderMedia = (recurso, isDetailed = false) => {
        if (recurso.tipo !== 'foto') return null;
        const filename = getMediaPath(recurso.contenido).split('/').pop();
        const imgUrl = `${MEDIA_BASE}/fotos/${filename}`;
        return (
            <div>
                <img src={imgUrl} className={isDetailed ? "preview-image" : "resource-image"} alt="Preview" />
                {isDetailed && <a href={imgUrl} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ display: 'inline-block', marginBottom: '1rem' }}>↗️ Abrir Original</a>}
            </div>
        );
    };

    const renderContent = (recurso, isDetailed = false) => {
        const { tipo, contenido } = recurso;
        if (tipo === 'link') return (
            <div>
                <a href={contenido} target="_blank" className="card-link" rel="noreferrer">🔗 {contenido}</a>
                {isDetailed && <div className="link-preview-container"><iframe src={contenido} title="Preview" loading="lazy"></iframe></div>}
            </div>
        );
        if (tipo === 'foto' || tipo === 'pdf') {
            const parts = contenido.split(/Archivo:/);
            const text = parts[0].trim();
            const filename = parts.length > 1 ? parts[1].trim().split('\\').pop().split('/').pop() : '';
            return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {text && <div>💬 {text}</div>}
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>📁 {filename || 'Archivo'}</div>
                    {isDetailed && tipo === 'pdf' && filename && <a href={`${MEDIA_BASE}/documentos/${filename}`} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ alignSelf: 'flex-start', marginTop: '1rem' }}>📄 Abrir PDF</a>}
                </div>
            );
        }
        return <div style={{ whiteSpace: 'pre-wrap' }}>{contenido}</div>;
    };

    const engineLabel = aiStatus ? (aiStatus.active_engine === 'deepseek' ? '🟢 DeepSeek' : aiStatus.active_engine === 'ollama' ? '🟡 Local' : '🔴 Sin IA') : '⏳';

    return (
        <div className="app-container">
            <div className="bg-blobs"><div className="blob blob-1"></div><div className="blob blob-2"></div></div>

            <aside className="sidebar">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ background: 'var(--accent)', padding: '0.5rem', borderRadius: '12px', display: 'flex', fontSize: '1.5rem' }}>🧠</div>
                    <div>
                        <h2 style={{ margin: 0 }}>Cerebro AI</h2>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{engineLabel}</span>
                    </div>
                </div>

                <div className="filter-section">
                    <h3>Vistas Rápidas</h3>
                    <button className={`filter-btn ${!filtroFav ? 'active' : ''}`} onClick={() => { setFiltroFav(false); setPage(0); }}>📚 Todos</button>
                    <button className={`filter-btn ${filtroFav ? 'active' : ''}`} onClick={() => { setFiltroFav(true); setPage(0); }}>⭐ Favoritos</button>
                </div>

                <div className="filter-section">
                    <h3>🤖 Herramientas IA</h3>
                    <button className="filter-btn" onClick={handleDigest} style={{ background: 'rgba(56,189,248,0.15)' }}>📰 Resumen Semanal</button>
                    <button className="filter-btn" onClick={() => setShowChat(!showChat)} style={{ background: 'rgba(129,140,248,0.15)' }}>💬 Chat con Notas</button>
                    <button className="filter-btn" onClick={handleBulkTag} disabled={bulkTagging} style={{ background: 'rgba(248,113,113,0.15)' }}>
                        {bulkTagging ? '⌛ Etiquetando...' : '🏷️ Etiquetar Todo'}
                    </button>
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
                    <h3>Orden</h3>
                    <select className="filter-btn" style={{ width: '100%' }} value={sortOrder} onChange={e => setSortOrder(e.target.value)}>
                        <option value="desc">🔽 Más recientes</option>
                        <option value="asc">🔼 Más antiguos</option>
                    </select>
                </div>

                <div style={{ marginTop: 'auto', padding: '1rem 0' }}>
                    <button className="btn btn-secondary" style={{ width: '100%', fontSize: '0.8rem', opacity: 0.7 }} onClick={() => setShowTaxonomy(true)}>🏷️ Ayuda Etiquetas</button>
                </div>
            </aside>

            <main className="main-content">
                <header className="header">
                    <div className="search-bar" style={{ position: 'relative' }}>
                        <span style={{ marginRight: '0.5rem' }}>{searchMode === 'semantic' ? '✨' : '🔍'}</span>
                        <input type="text" placeholder={searchMode === 'semantic' ? "Pregunta algo... (ej: ¿Qué herramientas de IA guardé?)" : "Buscar texto o etiquetas..."} value={search} onChange={e => setSearch(e.target.value)} />
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <div className="glass-panel" style={{ padding: '4px', borderRadius: '10px', display: 'flex' }}>
                            <button className={`btn-icon ${searchMode === 'normal' ? 'active' : ''}`} onClick={() => { setSearchMode('normal'); setPage(0); }} title="Búsqueda Normal">🔍</button>
                            <button className={`btn-icon ${searchMode === 'semantic' ? 'active' : ''}`} onClick={() => { setSearchMode('semantic'); setPage(0); }} title="Búsqueda IA">✨</button>
                        </div>
                        <div className="glass-panel" style={{ padding: '4px', borderRadius: '10px', display: 'flex' }}>
                            <button className={`btn-icon ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')}>🔲</button>
                            <button className={`btn-icon ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}>📜</button>
                        </div>
                    </div>
                </header>

                <div className={`content-scroll resource-container ${viewMode === 'list' ? 'list-view' : ''}`}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h2>
                            {searchMode === 'semantic' && searchTerm ? `✨ Resultados IA para "${search}"` : search ? `Resultados para "${search}"` : filtroFav ? 'Tus Favoritos' : 'Todos los Recursos'}
                            <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 'normal', marginLeft: '1rem' }}>({totalItems})</span>
                        </h2>
                    </div>

                    {loading ? (
                        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div><div>Cargando...</div>
                        </div>
                    ) : recursos.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '4rem', background: 'var(--card-bg)', borderRadius: '16px', border: '1px dashed var(--card-border)' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div><h3>No se encontraron resultados</h3>
                        </div>
                    ) : (
                        <div className="resource-grid">
                            {recursos.map(r => (
                                <div key={r.id} className="glass-panel resource-card">
                                    {viewMode === 'grid' && renderMedia(r)}
                                    <div className="card-header">
                                        <div className="card-type" style={{ color: 'var(--text-muted)' }}>{getTypeIcon(r.tipo)} {r.tipo.toUpperCase()}</div>
                                        <div className="card-date">{formatDate(r.fecha)}</div>
                                    </div>
                                    <div className="card-content" onClick={() => { setPreviewItem(r); setAiResult(""); }} style={{ cursor: 'pointer' }} title="Ampliar">
                                        {renderContent(r)}
                                    </div>
                                    <div className="card-tags">
                                        {r.etiqueta && r.etiqueta !== "SinEtiqueta" ? (
                                            r.etiqueta.split(',').map((t, i) => <span key={i} className="tag" onClick={() => setSearch(t.trim())}>#{t.trim()}</span>)
                                        ) : (
                                            <span className="tag" style={{ opacity: 0.5, borderColor: 'transparent', background: 'rgba(255,255,255,0.05)' }}>🏷️ Sin etiquetas</span>
                                        )}
                                    </div>
                                    <div className="card-actions">
                                        <button className={`btn-icon ${r.favorito ? 'active' : ''}`} onClick={() => toggleFav(r.id)}>{r.favorito ? '⭐' : '☆'}</button>
                                        <button className="btn-icon" onClick={() => setEditingItem(r)}>📝</button>
                                        <button className="btn-icon danger" onClick={() => deleteRecurso(r.id)}>🗑️</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {totalItems > limit && searchMode === 'normal' && (
                        <div className="pagination">
                            <button className="btn-page" disabled={page === 0} onClick={() => setPage(p => p - 1)}>◀ Anterior</button>
                            <span style={{ color: '#fff', fontSize: '1rem', fontWeight: 600 }}>Página {page + 1} de {Math.ceil(totalItems / limit)}</span>
                            <button className="btn-page" disabled={(page + 1) * limit >= totalItems} onClick={() => setPage(p => p + 1)}>Siguiente ▶</button>
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
                                <label>Contenido</label>
                                <textarea rows="6" value={editingItem.contenido} onChange={e => setEditingItem({ ...editingItem, contenido: e.target.value })} />
                            </div>
                            <div className="form-group">
                                <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    Etiquetas
                                    <button type="button" className="btn-ai" style={{ fontSize: '0.75rem' }} onClick={() => handleSuggestTags(editingItem.contenido)} disabled={aiLoading}>
                                        {aiLoading ? <span className="ai-loading">⌛</span> : '✨ Sugerir'}
                                    </button>
                                </label>
                                <input type="text" value={editingItem.etiqueta} onChange={e => setEditingItem({ ...editingItem, etiqueta: e.target.value })} placeholder="Ej: LaAgencia, Ideas" />
                            </div>
                            <div className="btn-group">
                                <button type="button" className="btn btn-secondary" onClick={() => setEditingItem(null)}>Cancelar</button>
                                <button type="submit" className="btn btn-primary">💾 Guardar</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Preview Modal */}
            {previewItem && (
                <div className="modal-overlay" onClick={() => setPreviewItem(null)} style={{ padding: '2rem' }}>
                    <div className="glass-panel modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '900px', width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
                        <div className="card-header" style={{ marginBottom: '1rem', position: 'sticky', top: 0, background: 'var(--card-bg)', zIndex: 10, padding: '1rem 0' }}>
                            <h2 style={{ margin: 0 }}>📖 Vista Detallada</h2>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button className="btn-ai" onClick={() => handleSummarize(previewItem.contenido)} disabled={aiLoading}>
                                    {aiLoading ? <span className="ai-loading">⌛</span> : '✨ Resumir'}
                                </button>
                                <button className="btn-icon" onClick={() => setPreviewItem(null)}>❌</button>
                            </div>
                        </div>
                        {aiResult && <div className="ai-result-box"><strong>🤖 Resumen IA:</strong> {aiResult}</div>}
                        <div style={{ marginBottom: '1rem' }}>{renderMedia(previewItem, true)}</div>
                        <div style={{ fontSize: '1.1rem', lineHeight: '1.6' }}>{renderContent(previewItem, true)}</div>
                        <div className="btn-group"><button className="btn btn-secondary" onClick={() => setPreviewItem(null)}>Cerrar</button></div>
                    </div>
                </div>
            )}

            {/* Digest Modal */}
            {showDigest && (
                <div className="modal-overlay" onClick={() => setShowDigest(false)}>
                    <div className="glass-panel modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', width: '90%' }}>
                        <div className="card-header" style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                            <h2 style={{ margin: 0 }}>📰 Resumen Semanal</h2>
                            <button className="btn-icon" onClick={() => setShowDigest(false)}>❌</button>
                        </div>
                        {aiLoading ? (
                            <div style={{ textAlign: 'center', padding: '3rem' }}><span className="ai-loading" style={{ fontSize: '2rem' }}>🧠</span><p>Generando resumen...</p></div>
                        ) : (
                            <div className="ai-result-box" style={{ whiteSpace: 'pre-wrap', fontSize: '1rem', lineHeight: '1.7' }}>{digestContent}</div>
                        )}
                        <div className="btn-group"><button className="btn btn-primary" onClick={() => setShowDigest(false)}>Cerrar</button></div>
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
                                    <li><strong>#LaAgencia:</strong> Clientes, operaciones.</li>
                                    <li><strong>#MiMarcaPersonal:</strong> Contenido, branding.</li>
                                    <li><strong>#Varios:</strong> Finanzas, vida, ideas.</li>
                                </ul>
                            </div>
                            <div className="taxonomy-col">
                                <h4>Nivel 2: Casos de Uso</h4>
                                <ul>
                                    <li><strong>#Ideas</strong> · <strong>#Herramientas</strong></li>
                                    <li><strong>#Referencias</strong> · <strong>#Proyectos</strong></li>
                                    <li><strong>#Novedades</strong> · <strong>#Prompt</strong></li>
                                </ul>
                            </div>
                        </div>
                        <div style={{ marginTop: '1.5rem', padding: '0.75rem', background: 'rgba(56,189,248,0.1)', borderRadius: '8px', fontSize: '0.85rem' }}>
                            💡 Usa una de <strong>Nivel 1</strong> + una de <strong>Nivel 2</strong> (ej: <code>#LaAgencia, #Ideas</code>)
                        </div>
                        <div className="btn-group"><button className="btn btn-primary" onClick={() => setShowTaxonomy(false)}>Entendido</button></div>
                    </div>
                </div>
            )}

            {/* Chat Floating Panel */}
            {showChat && (
                <div style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', width: '380px', maxHeight: '500px', zIndex: 1000, display: 'flex', flexDirection: 'column' }} className="glass-panel">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', borderBottom: '1px solid var(--card-border)' }}>
                        <strong>💬 Chat con tu Cerebro</strong>
                        <button className="btn-icon" onClick={() => setShowChat(false)} style={{ fontSize: '0.8rem' }}>❌</button>
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px' }}>
                        {chatMessages.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '2rem' }}>Hazle una pregunta sobre tus notas…</div>}
                        {chatMessages.map((m, i) => (
                            <div key={i} style={{
                                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                                background: m.role === 'user' ? 'var(--accent)' : 'rgba(255,255,255,0.1)',
                                color: '#fff', padding: '0.5rem 0.75rem', borderRadius: '12px',
                                maxWidth: '85%', fontSize: '0.9rem', lineHeight: '1.4', whiteSpace: 'pre-wrap'
                            }}>
                                {m.text}
                            </div>
                        ))}
                        {aiLoading && <div className="ai-loading" style={{ alignSelf: 'flex-start', padding: '0.5rem' }}>🧠 Pensando...</div>}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem 0.75rem', borderTop: '1px solid var(--card-border)' }}>
                        <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleChatSend()}
                            placeholder="Pregunta algo..." style={{ flex: 1, background: 'rgba(255,255,255,0.1)', border: '1px solid var(--card-border)', borderRadius: '8px', padding: '0.5rem', color: '#fff', fontSize: '0.85rem' }} />
                        <button className="btn-ai" onClick={handleChatSend} disabled={aiLoading} style={{ padding: '0.5rem 0.75rem' }}>→</button>
                    </div>
                </div>
            )}
        </div>
    );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
