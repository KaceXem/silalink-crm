import { useEffect, useState, useRef, useMemo } from "react";
import { getProspects, genererPitch, importProspectsCSV, deleteProspect, updatePitch, deleteDraft, Prospect } from "@/services/api";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { 
  RefreshCw, Sparkles, Building2, Mail, Eye, Upload, Trash2, 
  Search, Users, CheckCircle2, Clock, ArrowUpRight 
} from "lucide-react";

export default function App() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedProspect, setSelectedProspect] = useState<Prospect | null>(null);
  const [editedPitch, setEditedPitch] = useState<string>("");
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const fetchProspects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getProspects();
      setProspects(data);
    } catch {
      setError("Impossible de contacter le backend FastAPI. Vérifiez que les services sont actifs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProspects();
  }, []);

  const handleGenererPitch = async (id: number) => {
    try {
      setGeneratingId(id);
      await genererPitch(id);
      await fetchProspects();
    } catch {
      alert("Erreur lors de la génération du pitch.");
    } finally {
      setGeneratingId(null);
    }
  };

  const handleDelete = async (id: number, nomEntreprise: string) => {
    if (!window.confirm(`Supprimer définitivement le prospect "${nomEntreprise}" ?`)) return;
    try {
      setDeletingId(id);
      await deleteProspect(id);
      await fetchProspects();
    } catch {
      alert("Erreur lors de la suppression.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleUpdatePitch = async () => {
    if (!selectedProspect) return;
    setIsSaving(true);
    try {
      await updatePitch(selectedProspect.id, editedPitch);
      alert("Brouillon mis à jour avec succès dans Gmail !");
      setSelectedProspect(null);
      await fetchProspects();
    } catch {
      alert("Erreur lors de la mise à jour du brouillon.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteDraft = async (id: number) => {
    if (!window.confirm("Voulez-vous supprimer ce brouillon de Gmail et réinitialiser le prospect ?")) return;
    try {
      await deleteDraft(id);
      setSelectedProspect(null);
      await fetchProspects();
      alert("Brouillon supprimé de Gmail.");
    } catch {
      alert("Erreur lors de la suppression du brouillon.");
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await importProspectsCSV(file);
      alert(`Import réussi !\n- Ajoutés : ${result.added}\n- Doublons : ${result.duplicates}\n- Erreurs : ${result.errors}`);
      await fetchProspects();
    } catch {
      alert("Erreur lors de l'importation du fichier CSV.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Filtrage intelligent des prospects
  const filteredProspects = useMemo(() => {
    return prospects.filter((p) => {
      const name = (p.nom_entreprise || p.entreprise || "").toLowerCase();
      const contact = (p.contact || p.contact_nom || "").toLowerCase();
      const email = (p.email || "").toLowerCase();
      const matchesSearch = name.includes(searchTerm.toLowerCase()) || contact.includes(searchTerm.toLowerCase()) || email.includes(searchTerm.toLowerCase());
      
      const matchesStatus = statusFilter === "ALL" || p.statut === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [prospects, searchTerm, statusFilter]);

  // Statistiques dynamiques (KPIs)
  const stats = useMemo(() => {
    const total = prospects.length;
    const drafts = prospects.filter(p => p.statut === "BROUILLON_CREE").length;
    const pending = prospects.filter(p => !p.statut || p.statut === "EN ATTENTE").length;
    return { total, drafts, pending };
  }, [prospects]);

  const getBadgeVariant = (statut: string) => {
    switch (statut?.toUpperCase()) {
      case "BROUILLON_CREE": return "default";
      case "EN ATTENTE": return "secondary";
      case "PERDU": return "destructive";
      default: return "outline";
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans selection:bg-blue-600 selection:text-white">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* EN-TÊTE ÉLÉGANT */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-xl shadow-inner">
                SL
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                  SilaLink CRM <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">B2B Pro</span>
                </h1>
                <p className="text-sm text-slate-400">Plateforme unifiée d'acquisition et de génération de pitchs IA</p>
              </div>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3 items-center">
            <input type="file" accept=".csv" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
            
            <Button 
              onClick={() => fileInputRef.current?.click()} 
              disabled={isUploading} 
              className="bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20 transition-all flex items-center gap-2"
            >
              <Upload className={`h-4 w-4 ${isUploading ? "animate-bounce" : ""}`} />
              {isUploading ? "Traitement..." : "Importer un CSV"}
            </Button>

            <Button 
              variant="outline" 
              onClick={fetchProspects} 
              disabled={loading} 
              className="border-slate-700 bg-slate-800/50 hover:bg-slate-800 text-slate-200 transition-all flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> 
              Actualiser
            </Button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-950/50 border border-red-800/50 text-red-300 rounded-xl text-sm flex items-center gap-3 shadow-lg">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
            {error}
          </div>
        )}

        {/* BARRE DE MÉTRIQUES / KPI CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-sm hover:border-slate-700 transition-all">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Total Prospects</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.total}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Users className="h-6 w-6" />
            </div>
          </div>

          <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-sm hover:border-slate-700 transition-all">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Brouillons Gmail Prêts</p>
              <p className="text-3xl font-bold text-emerald-400 mt-1">{stats.drafts}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="h-6 w-6" />
            </div>
          </div>

          <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-sm hover:border-slate-700 transition-all">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">En Attente de Pitch</p>
              <p className="text-3xl font-bold text-amber-400 mt-1">{stats.pending}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Clock className="h-6 w-6" />
            </div>
          </div>
        </div>

        {/* SECTION PRINCIPALE : TABLEAU ET FILTRES */}
        <Card className="bg-slate-800/40 border-slate-800 shadow-xl rounded-2xl overflow-hidden backdrop-blur-sm">
          <CardHeader className="border-b border-slate-800 px-6 py-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-800/20">
            <CardTitle className="text-lg font-semibold flex items-center gap-2 text-white">
              <Building2 className="h-5 w-5 text-blue-400" /> Répertoire des Prospects
            </CardTitle>

            {/* FILTRES DE RECHERCHE */}
            <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Rechercher entreprise, contact..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-all"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
              >
                <option value="ALL">Tous les statuts</option>
                <option value="EN ATTENTE">En attente</option>
                <option value="BROUILLON_CREE">Brouillon créé</option>
              </select>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 bg-slate-900/40 hover:bg-slate-900/40">
                  <TableHead className="w-[70px] text-slate-400 font-semibold">ID</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Entreprise</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Contact Clé</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Email Professionnel</TableHead>
                  <TableHead className="text-slate-400 font-semibold">Statut</TableHead>
                  <TableHead className="text-right text-slate-400 font-semibold">Actions Commerciales</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && filteredProspects.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-slate-500">
                      Chargement des données en cours...
                    </TableCell>
                  </TableRow>
                ) : filteredProspects.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-slate-500">
                      Aucun prospect ne correspond à vos critères.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredProspects.map((p) => {
                    const nomEntreprise = p.nom_entreprise || p.entreprise || "—";
                    const nomContact = p.contact || p.contact_nom || p.nom || "—";
                    return (
                      <TableRow key={p.id} className="border-slate-800/60 hover:bg-slate-800/30 transition-colors group">
                        <TableCell className="font-mono text-xs text-slate-400">#{p.id}</TableCell>
                        <TableCell className="font-medium text-white group-hover:text-blue-400 transition-colors">
                          {nomEntreprise}
                        </TableCell>
                        <TableCell className="text-slate-300">{nomContact}</TableCell>
                        <TableCell className="text-slate-400">
                          <span className="flex items-center gap-2 text-xs">
                            <Mail className="h-3.5 w-3.5 text-slate-500" />
                            {p.email}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getBadgeVariant(p.statut)} className="px-2.5 py-1 text-[10px] tracking-wide font-semibold shadow-sm">
                            {p.statut || "EN ATTENTE"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            {p.statut === "BROUILLON_CREE" && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSelectedProspect(p);
                                  setEditedPitch(p.pitch_genere || p.pitch_commercial || "");
                                }}
                                className="border-slate-700 bg-slate-800/40 hover:bg-slate-700 text-slate-200 h-8 px-3 text-xs gap-1.5"
                              >
                                <Eye className="h-3.5 w-3.5 text-blue-400" /> Voir / Éditer
                              </Button>
                            )}
                            <Button
                              size="sm"
                              disabled={generatingId === p.id}
                              onClick={() => handleGenererPitch(p.id)}
                              className="bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 h-8 px-3 text-xs gap-1.5 transition-all"
                            >
                              <Sparkles className={`h-3.5 w-3.5 text-amber-400 ${generatingId === p.id ? "animate-spin" : ""}`} />
                              {generatingId === p.id ? "IA en cours..." : "Générer Pitch"}
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              disabled={deletingId === p.id}
                              onClick={() => handleDelete(p.id, nomEntreprise)}
                              className="h-8 w-8 text-slate-500 hover:text-red-400 hover:bg-red-950/30 transition-all rounded-lg"
                              title="Supprimer ce prospect"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* MODAL DE VISUALISATION ET D'ÉDITION DU PITCH */}
        <Dialog open={!!selectedProspect} onOpenChange={() => setSelectedProspect(null)}>
          <DialogContent className="max-w-2xl bg-slate-900 border border-slate-800 text-slate-100 shadow-2xl rounded-2xl p-6">
            <DialogHeader className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
                  <ArrowUpRight className="h-3 w-3" /> Brouillon Gmail Actif
                </span>
              </div>
              <DialogTitle className="text-xl font-bold text-white">
                Édition du Pitch — {selectedProspect?.nom_entreprise || selectedProspect?.entreprise}
              </DialogTitle>
              <DialogDescription className="text-slate-400 text-xs">
                Modifiez le texte ci-dessous pour impacter directement le brouillon dans Gmail.
              </DialogDescription>
            </DialogHeader>

            <div className="mt-4 space-y-4">
              <textarea
                value={editedPitch}
                onChange={(e) => setEditedPitch(e.target.value)}
                className="w-full h-60 bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 focus:outline-none focus:border-blue-500 leading-relaxed resize-none shadow-inner"
              />

              <div className="flex justify-between items-center pt-2">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => selectedProspect && handleDeleteDraft(selectedProspect.id)}
                  className="bg-red-950/50 hover:bg-red-900/50 text-red-300 border border-red-800/50 gap-2"
                >
                  <Trash2 className="h-4 w-4" /> Supprimer le brouillon Gmail
                </Button>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedProspect(null)}
                    className="border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                  >
                    Annuler
                  </Button>
                  <Button
                    size="sm"
                    disabled={isSaving}
                    onClick={handleUpdatePitch}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2"
                  >
                    {isSaving ? "Enregistrement..." : "Enregistrer les modifications"}
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

      </div>
    </div>
  );
}