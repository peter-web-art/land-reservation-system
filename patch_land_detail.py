import sys

path = r'lands/templates/lands/land_detail.html'
content = open(path, encoding='utf-8').read()

# Normalize line endings
c = content.replace('\r\n', '\n')

fixes = 0

# ─── Fix 1: Contact Owner button – only customer role; admin gets View Reports link ───
old1 = """          {% if user != land.owner %}
          <button onclick="document.getElementById('msgOwnerModal').classList.remove('hidden');" class="w-full mt-2 px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:border-gray-400 hover:bg-gray-50 transition-colors">
            Contact Owner
          </button>
          {% endif %}
        {% elif user.is_authenticated and user.role == 'admin' %}
          <div class="mt-4 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-center">
            Admin accounts are not allowed to book land.
          </div>
          {% if user != land.owner %}
          <button onclick="document.getElementById('msgOwnerModal').classList.remove('hidden');" class="w-full mt-2 px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:border-gray-400 hover:bg-gray-50 transition-colors">
            Contact Owner
          </button>
          {% endif %}"""

new1 = """          {% if user != land.owner and user.role == 'customer' %}
          <button onclick="document.getElementById('msgOwnerModal').classList.remove('hidden');" class="w-full mt-2 px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:border-gray-400 hover:bg-gray-50 transition-colors">
            <i class="bi bi-chat-dots mr-1"></i> Contact Owner
          </button>
          {% endif %}
        {% elif user.is_authenticated and user.role == 'admin' %}
          <div class="mt-4 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-center text-sm">
            <i class="bi bi-shield-lock mr-1"></i> Admin accounts cannot book land.
          </div>
          {% if user != land.owner %}
          <a href="{% url 'lands:admin_reported_lands' %}"
            class="block w-full mt-2 px-6 py-2.5 border border-red-300 text-red-700 rounded-lg font-semibold text-sm text-center hover:bg-red-50 transition-colors no-underline">
            <i class="bi bi-flag mr-1"></i> View Land Reports
          </a>
          {% endif %}"""

if old1 in c:
    c = c.replace(old1, new1)
    fixes += 1
    print('Fix 1 applied: Contact Owner / Admin button')
else:
    print('Fix 1 NOT FOUND - skipped')

# ─── Fix 2: Report button – only non-owners ───
old2 = """        {% if user.is_authenticated %}
        <div class="mt-4 text-center">
          <button onclick="document.getElementById('reportModal').classList.remove('hidden');" class="bg-transparent border-none text-gray-500 text-sm underline cursor-pointer">
            Report this land
          </button>
        </div>
        {% endif %}"""

new2 = """        {% if user.is_authenticated and user != land.owner %}
        <div class="mt-4 text-center">
          <button onclick="document.getElementById('reportModal').classList.remove('hidden');" class="bg-transparent border-none text-gray-500 text-sm underline cursor-pointer hover:text-red-600 transition-colors">
            <i class="bi bi-flag text-xs"></i> Report this land
          </button>
        </div>
        {% endif %}"""

if old2 in c:
    c = c.replace(old2, new2)
    fixes += 1
    print('Fix 2 applied: Report button restricted to non-owners')
else:
    print('Fix 2 NOT FOUND - skipped')

# ─── Fix 3: Report modal – add reason dropdown + description field, restrict to non-owners ───
old3 = """<!-- Report Modal -->
{% if user.is_authenticated %}
<div class="fixed inset-0 z-[60] bg-black/50 hidden flex items-center justify-center" id="reportModal" onclick="if(event.target===this)this.classList.add('hidden')">
  <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
    <div class="flex items-center justify-between p-4 border-b border-gray-200">
      <h3 class="font-semibold flex items-center gap-2"><i class="bi bi-flag"></i> Report Land</h3>
      <button onclick="document.getElementById('reportModal').classList.add('hidden')" class="text-2xl text-gray-400 hover:text-gray-600">&times;</button>
    </div>
    <div class="p-4">
      <form method="post" action="{% url 'lands:report_listing' land.id %}">
        {% csrf_token %}
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Reason</label>
          <textarea name="reason" rows="4" class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38]" placeholder="Describe the issue..." required></textarea>
        </div>
        <button type="submit" class="w-full py-2.5 bg-red-600 text-white rounded-lg font-semibold text-sm hover:bg-red-700 transition-colors"><i class="bi bi-flag"></i> Submit Report</button>
      </form>
    </div>
  </div>
</div>
{% endif %}"""

new3 = """<!-- Report Modal -->
{% if user.is_authenticated and user != land.owner %}
<div class="fixed inset-0 z-[60] bg-black/50 hidden flex items-center justify-center" id="reportModal" onclick="if(event.target===this)this.classList.add('hidden')">
  <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
    <div class="flex items-center justify-between p-4 border-b border-gray-200">
      <h3 class="font-semibold flex items-center gap-2"><i class="bi bi-flag text-red-500"></i> Report This Land</h3>
      <button onclick="document.getElementById('reportModal').classList.add('hidden')" class="text-2xl text-gray-400 hover:text-gray-600">&times;</button>
    </div>
    <div class="p-4">
      <form method="post" action="{% url 'lands:report_listing' land.id %}">
        {% csrf_token %}
        <div class="mb-3">
          <label class="block text-sm font-medium text-gray-700 mb-1.5">Reason <span class="text-red-500">*</span></label>
          <select name="reason" required
            class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500/30 focus:border-red-500 transition-colors">
            <option value="">-- Select a reason --</option>
            <option value="spam">Spam or Misleading</option>
            <option value="fake">Fake or Fraudulent</option>
            <option value="illegal">Illegal Activity</option>
            <option value="harassment">Harassment or Abuse</option>
            <option value="scam">Suspected Scam</option>
            <option value="inappropriate">Inappropriate Content</option>
            <option value="duplicate">Duplicate Listing</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1.5">Description <span class="text-red-500">*</span></label>
          <textarea name="description" rows="4"
            class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500/30 focus:border-red-500 transition-colors"
            placeholder="Please describe the issue in detail..." required></textarea>
        </div>
        <div class="flex items-start gap-2 p-3 bg-amber-50 border border-amber-100 rounded-lg mb-4">
          <i class="bi bi-info-circle text-amber-600 mt-0.5 flex-shrink-0 text-sm"></i>
          <p class="text-xs text-amber-700 m-0">Reports are reviewed by our team within 24-48 hours. False reports may result in account action.</p>
        </div>
        <button type="submit" class="w-full py-2.5 bg-red-600 text-white rounded-lg font-semibold text-sm hover:bg-red-700 transition-colors">
          <i class="bi bi-flag mr-1"></i> Submit Report
        </button>
      </form>
    </div>
  </div>
</div>
{% endif %}"""

if old3 in c:
    c = c.replace(old3, new3)
    fixes += 1
    print('Fix 3 applied: Report modal updated with proper fields')
else:
    print('Fix 3 NOT FOUND - skipped')

print(f'\nTotal fixes applied: {fixes}/3')
open(path, 'w', encoding='utf-8').write(c)
print('File saved.')
