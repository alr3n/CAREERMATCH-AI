import { PageHeader } from "../components/AppShell";
import { ProfileEditor } from "../components/ProfileEditor";
import { ErrorState, LoadingState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";

export function PreferencesPage() {
  const { profile, setProfile } = useAuth();
  const facets = useAsync(() => api.facets(), []);
  if (!profile) return <LoadingState />;
  return (
    <>
      <PageHeader
        title="Job preferences"
        description="Everything here is optional. Preferences change how jobs are ranked; leaving something empty means it isn't used in scoring."
      />
      {facets.error && <ErrorState error={facets.error} title="Couldn't load suggestions" />}
      <div className="panel max-w-3xl p-6">
        <ProfileEditor
          profile={profile.profile}
          suggestions={{
            locations: facets.data?.locations.map((l) => l.value).filter((l) => l !== "Unspecified"),
            skills: facets.data?.skills.map((s) => s.value),
          }}
          onSave={async (update) => setProfile(await api.updateProfile(update))}
        />
      </div>
    </>
  );
}
