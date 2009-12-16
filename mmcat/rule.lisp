;---------------------------------------------
; defflavor rule
; defun make-relation-rule
; defun make-non-relation-rule
;---------------------------------------------

;---------------------------------------------
; rule.relation?
;---------------------------------------------

;---------------------------------------------
; rule.no-change?
;---------------------------------------------

;---------------------------------------------
; rule.print | REMOVED
;---------------------------------------------

;---------------------------------------------
; rule-equal? | Rule.__eq__
;---------------------------------------------
 
;---------------------------------------------
; rule-scout | RuleScout
;---------------------------------------------

;---------------------------------------------
; rule-strength-tester | RuleStrengthTester
;---------------------------------------------

;---------------------------------------------
; rule-builder | RuleBuilder
;---------------------------------------------

;---------------------------------------------
; build-rule | Workspace.build_rule
;---------------------------------------------

;---------------------------------------------
; build-translated-rule | Workspace.build_translated_rule
;---------------------------------------------

;---------------------------------------------
; break-rule | Workspace.break_rule
;---------------------------------------------

(defun rule-translator (&aux slippage-list answer-temperature-threshold 
			     changed-obj changed-obj-correspondence
			     new-translated-rule)
; This codelet translates the rule according to the translation rules given 
; in the slippages on the workspace.
(block nil
  (if* %verbose% then (format t "In rule-translator~&"))

  ; If no rule, fizzle.
  (if* (null *rule*) 
   then (if* %verbose% 
         then (format t "No rule.  Fizzling.~&"))
        (return))

  (if* (send *rule* :no-change?)
   then (setq *translated-rule* 
	      (make-non-relation-rule nil nil nil nil nil nil))
        (if* %workspace-graphics% 
         then (send *translated-rule* :draw %translated-rule-mode%))
	(return))

  ; If the temperature is too high (a threshold is probabilistically chosen), 
  ; then fizzle.
   (setq answer-temperature-threshold 
	 (send (get-answer-temperature-threshold-distribution) :choose))
   (if* %verbose%
    then (format t "The answer-temperature-threshold is ~a~&" 
		 answer-temperature-threshold))
   (if* (> *temperature* answer-temperature-threshold)
   then (if* %verbose% 
	 then (format t "Temperature too high.  Fizzling.~&"))
        (return))

  ; Otherwise build translation of rule.

  ; Find changed object.
  (setq changed-obj (loop for obj in (send *initial-string* :object-list)
			  when (send obj :changed?) return obj
			  finally (return nil)))
	
  ; If no changed object, then fizzle.
  (if* (null changed-obj) 
   then (if* %verbose% 
         then (format t "There is no changed object.~&"))
        (return))

  (setq changed-obj-correspondence (send changed-obj :correspondence))

  ; Get slippages to use.
  (setq slippage-list (send *workspace* :slippage-list))
  (if* changed-obj-correspondence
   then (loop for s in (send *workspace* :slippage-list) do
	      (loop for cm in (send changed-obj-correspondence 
				    :concept-mapping-list) 
	            when (contradictory-concept-mappings? cm s) do
	                 (setq slippage-list (remove s slippage-list)))))
	      
  (setq new-translated-rule 
	(if* (send *rule* :relation?)
         then (make-relation-rule 
		  (send (send *rule* :object-category1) 
			:apply-slippages slippage-list)
	          (send (send *rule* :descriptor1-facet) 
			:apply-slippages slippage-list)
	          (send (send *rule* :descriptor1) 
			:apply-slippages slippage-list)
	          (send (send *rule* :object-category2) 
			:apply-slippages slippage-list)
 	          (send (send *rule* :replaced-description-type) 
			:apply-slippages slippage-list)
                  (send (send *rule* :relation) 
			:apply-slippages slippage-list))
	 else (make-non-relation-rule 
		  (send (send *rule* :object-category1) 
			:apply-slippages slippage-list)
	          (send (send *rule* :descriptor1-facet) 
			:apply-slippages slippage-list)
	          (send (send *rule* :descriptor1) 
			:apply-slippages slippage-list)
	          (send (send *rule* :object-category2) 
			:apply-slippages slippage-list)
	          (send (send *rule* :replaced-description-type) 
			:apply-slippages slippage-list)
	          (send (send *rule* :descriptor2) 
			:apply-slippages slippage-list))))

  (build-translated-rule new-translated-rule)))    

;---------------------------------------------

(defun propose-rule (i-obj i-description m-obj m-description
	             &aux proposed-rule urgency)
; Creates a proposed rule, and posts a rule-strength-tester codelet with 
; urgency a function of the degree of conceptual-depth of the descriptions in the 
; rule.

  (if* (null i-obj)
   then (setq proposed-rule (make-non-relation-rule nil nil nil nil nil nil))
   else (if* (typep m-description 'extrinsic-description)
         then (setq proposed-rule 
	            (make-relation-rule 
		       (send i-obj :get-descriptor plato-object-category)
                       (send i-description :description-type)
                       (send i-description :descriptor)
		       (send m-obj :get-descriptor plato-object-category)
 	               (send m-description :description-type-related)
	               (send m-description :relation)))
         else (setq proposed-rule 
	            (make-non-relation-rule 
                        (send i-obj :get-descriptor plato-object-category)
                        (send i-description :description-type)
 	                (send i-description :descriptor)
		        (send m-obj :get-descriptor plato-object-category)
	                (send m-description :description-type)
	                (send m-description :descriptor)))))

  (if* %verbose% 
   then (format t "The proposed rule is:~&") (send proposed-rule :print) 
        (format t "~%"))

  (if* (null i-description)
   then (setq urgency 100)
   else ; The average alone is too low for low-conceptual-depth rules.
        (setq urgency 
	      (* 100 (sqrt (/ (average (send i-description :conceptual-depth)
		                       (send m-description :conceptual-depth))
  			      100)))))

  (if* %verbose% 
   then (format t "Posting a rule-strength-tester with urgency ~a~&" 
		(get-urgency-bin urgency)))
  (send *coderack* :post 
        (make-codelet 'rule-strength-tester (list proposed-rule)
	              (get-urgency-bin urgency))))

;---------------------------------------------
; activate-from-workspace-rule-descriptions | Workspace.activate_from_workspace_rule_descriptions
;---------------------------------------------


