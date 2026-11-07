<?php

namespace App\Http\Controllers;

use App\Enums\Role;
use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\Rules\Password;
use Illuminate\Validation\ValidationException;

class UserController extends Controller
{
    public function index()
    {
        return view('users.index', ['users' => User::orderBy('name')->paginate(20)]);
    }

    public function create()
    {
        return view('users.form', ['account' => new User, 'roles' => Role::cases()]);
    }

    public function edit(User $user)
    {
        return view('users.form', ['account' => $user, 'roles' => Role::cases()]);
    }

    private function validated(Request $request, ?User $user = null): array
    {
        if (is_string($request->input('username'))) {
            $request->merge(['username' => Str::lower(trim($request->input('username')))]);
        }
        if (is_string($request->input('email'))) {
            $request->merge(['email' => Str::lower(trim($request->input('email')))]);
        }

        return $request->validate([
            'name' => ['required', 'string', 'max:100'],
            'username' => ['required', 'string', 'regex:/^[a-z][a-z0-9_]{2,31}$/', Rule::unique('users')->ignore($user?->id)],
            'email' => ['required', 'email', 'max:254', Rule::unique('users')->ignore($user?->id)],
            'password' => [$user ? 'nullable' : 'required', 'string', Password::min(15), 'max:256', 'confirmed'],
            'roles' => ['required', 'array', 'min:1', 'max:4'],
            'roles.*' => ['required', Rule::enum(Role::class), 'distinct'],
            'active' => ['required', 'boolean'],
            'version' => [$user ? 'required' : 'nullable', 'integer', 'min:1'],
        ]);
    }

    public function store(Request $request)
    {
        $data = $this->validated($request);
        $user = new User;
        $user->name = $data['name'];
        $user->username = $data['username'];
        $user->email = $data['email'];
        $user->password = $data['password'];
        $user->roles = $data['roles'];
        $user->active = $data['active'];
        $user->save();

        return redirect()->route('users.index')->with('status', 'Akun berhasil dibuat.');
    }

    public function update(Request $request, User $user)
    {
        $data = $this->validated($request, $user);
        DB::transaction(function () use ($data, $user, $request) {
            $accounts = User::orderBy('id')->lockForUpdate()->get();
            $target = $accounts->firstWhere('id', $user->id);
            $actor = $accounts->firstWhere('id', $request->user()->id);
            abort_unless($actor?->hasRole(Role::Admin) && $request->session()->get('auth_version') === $actor->auth_version, 403);
            abort_unless($target, 404);
            if ($target->auth_version !== (int) $data['version']) {
                throw ValidationException::withMessages(['version' => 'Akun sudah berubah. Muat ulang halaman sebelum menyimpan.']);
            }
            $roles = $data['roles'];
            sort($roles);
            $existing = $target->roles;
            sort($existing);
            if ($target->is($actor) && (! $data['active'] || $roles !== $existing)) {
                throw ValidationException::withMessages(['roles' => 'Role dan status akun sendiri tidak dapat diubah.']);
            }
            if ($target->hasRole(Role::Admin) && (! $data['active'] || ! in_array(Role::Admin->value, $roles, true))) {
                if (! $accounts->contains(fn (User $other) => ! $other->is($target) && $other->hasRole(Role::Admin))) {
                    throw ValidationException::withMessages(['roles' => 'Minimal satu administrator aktif harus tersedia.']);
                }
            }
            $target->name = $data['name'];
            $target->username = $data['username'];
            $target->email = $data['email'];
            $target->roles = $roles;
            $target->active = $data['active'];
            if (! empty($data['password'])) {
                $target->password = $data['password'];
            }
            $target->auth_version++;
            $target->save();
        });

        return redirect()->route('users.index')->with('status', 'Akun diperbarui. Sesi sebelumnya telah dicabut.');
    }
}
