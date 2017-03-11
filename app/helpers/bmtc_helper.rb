module BmtcHelper
	def self.remove_tags(string)
		sanitized = ActionController::Base.helpers.strip_tags(string.to_s)
		return sanitized
	end
end
